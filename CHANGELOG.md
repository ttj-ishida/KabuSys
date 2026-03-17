Keep a Changelog に準拠した CHANGELOG.md (日本語)
すべての注目すべき変更を記録します。  

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 

## [0.1.0] - 2026-03-17
初回リリース — KabuSys のコアモジュールを追加しました。以下はコードベースから推測できる主要な機能と設計上の注意点です。

### 追加
- パッケージ基盤
  - パッケージ名: KabuSys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - エクスポート: data, strategy, execution, monitoring を公開

- 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数読み込み機能を実装
  - プロジェクトルート検出 (.git または pyproject.toml を起点) により CWD 非依存で自動ロード
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション
  - export KEY=val、クォート、インラインコメントなどに対応する .env パーサ
  - OS 環境変数の保護（protected set）を考慮した上書き制御
  - 必須キー取得ヘルパー _require と Settings クラスを提供
  - Settings に J-Quants / kabu / Slack / DB パス / 環境・ログレベル判定プロパティを実装
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL）の検査ロジック

- J‑Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出し wrapper と JSON パース
  - レートリミッタ実装（120 req/min、固定間隔スロットリング）
  - 再試行ロジック（指数バックオフ、最大試行回数 3、408/429/5xx を対象）
  - 401 受信時にリフレッシュトークンで id_token を自動更新して 1 回リトライ
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）
  - データ取得関数:
    - fetch_daily_quotes (ページネーション対応)
    - fetch_financial_statements (ページネーション対応)
    - fetch_market_calendar
  - DuckDB への保存関数（冪等性を確保する ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - fetched_at に UTC タイムスタンプを付与し Look‑ahead Bias を抑制
  - 型変換ユーティリティ (_to_float, _to_int)

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードから記事収集、前処理、DuckDB への冪等保存ワークフロー実装
  - 設計上のセキュリティと堅牢性:
    - defusedxml による XML パース（XML Bomb 等対策）
    - SSRF 対策: URL スキーム検証、ホストのプライベートアドレス判定、リダイレクト検査用ハンドラ
    - レスポンス受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再検査
    - HTTP ヘッダ User-Agent の設定、gzip 対応
    - トラッキングパラメータ (utm_, fbclid 等) の除去と URL 正規化
    - 記事 ID は正規化 URL の SHA‑256 の先頭 32 文字で生成（冪等性保証）
  - データ保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id を用いて新規挿入 ID を返す（チャンク & 単一トランザクション）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンク INSERT（ON CONFLICT DO NOTHING）で保存
  - 銘柄抽出:
    - extract_stock_codes: テキスト中の 4 桁数字を known_codes と照合して抽出
  - run_news_collection: 複数 RSS ソースを独立して取得し、失敗ソースをスキップして継続する集約ジョブを実装
  - テスト容易性: _urlopen を差し替え（モック）可能な設計

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - 3 層アーキテクチャに基づくテーブル群を定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な CHECK 制約、PRIMARY KEY、外部キーを設定
  - インデックス定義（頻出クエリに対する index を作成）
  - init_schema(db_path): 親ディレクトリ自動作成、DDL 実行、冪等にテーブル作成
  - get_connection(db_path): 既存 DB 接続返却（スキーマ初期化は行わない）

- ETL パイプライン骨組み (src/kabusys/data/pipeline.py)
  - 差分更新を行うためのヘルパー関数:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date
    - _table_exists, _get_max_date
  - 市場カレンダー補助: _adjust_to_trading_day（非営業日を直近営業日に補正）
  - ETLResult dataclass: ETL 実行結果、品質問題リスト、エラーリスト、ユーティリティ to_dict、has_errors/has_quality_errors を提供
  - run_prices_etl のスケルトン（差分計算、backfill_days による再取得、jq.fetch_daily_quotes → jq.save_daily_quotes を呼ぶ流れ）を実装
  - 設計方針（コード内コメントより）:
    - デフォルト差分単位は営業日 1 日分
    - backfill_days デフォルト 3（日）で後出し修正を吸収
    - カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）などの方針

### 改善 / 設計上の注記
- テスト容易性のために id_token 注入や _urlopen の差し替えを想定した設計が行われている
- 冪等な DB 操作（ON CONFLICT）やトランザクションロールバック処理により一貫性を重視
- ネットワーク呼び出しに対して明確なタイムアウトやバックオフ戦略を採用
- セキュリティ面では SSRF 対策や XML パースの安全化、受信サイズ制限などを実装

### 既知の未完事項（コードから推測）
- pipeline.run_prices_etl の戻り値部分が途中で切れている（len(records), で終わっている）ため、完全な実装が残っている可能性あり
- strategy/execution/monitoring の各パッケージ初期化ファイルは存在するが具体的な実装はこのリリースに含まれていない（スケルトン）

### セキュリティ
- ニュース収集における SSRF 対策、defusedxml の採用、受信サイズ制限、URL スキーム検査等のセキュリティ設計を追加

## 参考
- 環境変数読み込み: KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して自動ロードを無効化可能
- J-Quants API レート制限: 120 req/min（_MIN_INTERVAL_SEC = 60 / 120）
- ニュース最大受信サイズ: 10 MB（MAX_RESPONSE_BYTES）

---
（この CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際の変更履歴を反映する場合はコミット履歴やリリースノートと照合してください。）