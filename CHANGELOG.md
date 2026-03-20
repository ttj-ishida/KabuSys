# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはソースコードから推測して作成しています（初回リリース相当: v0.1.0）。

## [0.1.0] - 2026-03-20

### Added
- 初回リリース: kabusys パッケージ全体を追加。
  - パッケージメタ:
    - バージョン: 0.1.0
    - パブリック API (src/kabusys/__init__.py): data, strategy, execution, monitoring を __all__ として公開（execution は現状空パッケージ）。
- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を自動的に読み込む機能を実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して検出（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込みを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ:
    - `export KEY=val` 形式対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの扱い（クォート有無でのコメント判定）。
  - Settings クラス（settings インスタンスを公開）:
    - 必須設定取得のヘルパー `_require`（未設定時は ValueError）。
    - J-Quants / kabu / Slack / DB パス等のプロパティを定義（デフォルト値やパス展開を含む）。
    - `KABUSYS_ENV` 値検証（"development", "paper_trading", "live" のみ許容）。
    - `LOG_LEVEL` 値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - ユーティリティプロパティ: is_live / is_paper / is_dev。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API レート制御: 固定間隔スロットリングで 120 req/min を実現する RateLimiter 実装。
  - 再試行ロジック:
    - 指数バックオフを用いた最大 3 回のリトライ（ネットワーク/一部 HTTP ステータス 408, 429, 5xx 対象）。
    - 429 時は `Retry-After` ヘッダを優先。
  - 認証:
    - リフレッシュトークン -> ID トークン取得 (get_id_token)。
    - 401 を受けた場合に ID トークンを自動リフレッシュして 1 回だけ再試行する仕組み。
    - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（pagination_key によるループ）。
  - DuckDB への保存ユーティリティ（冪等）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
    - INSERT ... ON CONFLICT DO UPDATE を利用して重複を排除。PK 欠損レコードはスキップしてログ出力。
    - fetched_at を UTC ISO (Z) で記録。
    - 値変換ユーティリティ: _to_float, _to_int（堅牢な変換・不正値の扱いを明記）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と raw_news への冪等保存を想定した実装（設計に基づく実装多数）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策等）。
    - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）。
    - 受信最大バイト数制限 (MAX_RESPONSE_BYTES = 10MB) によりメモリ DoS を緩和。
    - 記事 ID の生成（URL 正規化後の SHA-256 の先頭等を想定）により冪等性を担保する設計。
  - データ処理:
    - テキスト前処理（URL 除去・空白正規化）等、DB へのバルク INSERT をチャンク化して高速化。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。
- 研究用モジュール (src/kabusys/research)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率の計算。
    - calc_volatility: 20 日 ATR（atr_pct）、20 日平均売買代金、出来高比率等の計算。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算（EPS = 0 / 欠損時は None）。
    - SQL を中心に DuckDB 上で完結する実装。営業日欠損をカバーするスキャン範囲の工夫あり。
  - feature_exploration.py:
    - calc_forward_returns: 与えたホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を実装（同順位は平均ランク処理）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー。
    - rank: 値リストをランクに変換（同順位は平均ランク、丸めによる ties 対策）。
  - research パッケージ __init__ で主要関数を公開。
- 戦略モジュール (src/kabusys/strategy)
  - feature_engineering.py:
    - build_features: research の生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）適用、数値ファクターを Z スコア正規化（外れ値を ±3 でクリップ）、features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ユニバース閾値: 最低株価 300 円、最低平均売買代金 5 億円。
    - 研究データからのルックアヘッドバイアス防止を意識した設計。
  - signal_generator.py:
    - generate_signals: features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ日付単位で置換。
    - デフォルト重みと閾値:
      - weights デフォルト: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
      - BUY 閾値: 0.60
    - 重みの検証・補完・再スケーリング機能を実装（未知キー・非数値・負値は無視）。
    - AI スコアはシグモイド変換して統合。未登録は中立値（0.5）で補完。
    - Bear レジーム判定: ai_scores の regime_score 平均が負かつサンプル数 >= 3 の場合に BUY を抑制。
    - SELL (エグジット) ロジック:
      - ストップロス: 現価 / avg_price - 1 < -8% で即時 SELL（最優先）。
      - final_score が閾値未満の場合 SELL。
      - positions テーブルの価格欠損時は判定をスキップしてログ出力。
    - BUY と SELL の優先ポリシー（SELL を優先して BUY から除外）、signals テーブルへのトランザクション置換で原子性を確保。
    - 未実装のエグジット条件（実装予定の設計メモ）:
      - トレーリングストップ（peak_price が必要）
      - 時間決済（保有日数ベース）
- ロギング: 各主要処理に対して info/debug/warning レベルで実行ログを出力するよう設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- XML パースに defusedxml を利用（news_collector）。
- RSS 受信サイズ上限や URL 正規化など SSRF / DoS 対策の設計を反映。
- J-Quants クライアントは認証トークンの自動リフレッシュ時に無限再帰を防止（allow_refresh フラグ）する仕組みを入れている。

### Known limitations / Notes
- signals / features / prices_daily / raw_financials / raw_prices / positions 等の DuckDB テーブルは事前にスキーマを用意する必要がある（スキーマ生成ロジックは本コードに含まれていない）。
- 一部エグジット条件（トレーリングストップ、時間決済）は設計メモとして存在するが未実装。
- news_collector の一部実装（記事 ID 生成・SQL の INSERT RETURNING 周り）は設計方針が示されているが、外部依存（HTTP フィードの取り扱い実装など）に注意が必要。
- 外部ライブラリ依存: duckdb, defusedxml を利用。実行環境にこれらが必要。
- J-Quants API のレート制限やネットワーク障害に備えたリトライロジックはあるが、運用上はさらに監視 / バックオフ調整が推奨される。

---

（以降のリリースでは Added/Changed/Fixed 等を追記してください。）