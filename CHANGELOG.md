# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、公開の互換性方針はセマンティックバージョニングに従います。

※ この CHANGELOG は与えられたコードベースの内容から推測して作成しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主要な機能群はデータ取得・保存、リサーチ（ファクター計算・解析）、特徴量エンジニアリング、シグナル生成、環境設定です。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名・バージョン定義と公開モジュール一覧を追加。

- 環境設定 / ロード
  - src/kabusys/config.py:
    - .env/.env.local ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
    - .env パーサを実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント処理に対応）。
    - 設定値アクセス用 Settings クラスを提供（J-Quants, kabuステーション, Slack, DB パス, 環境判定, ログレベル等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py:
    - API 呼び出しユーティリティ（_request）を実装。固定間隔レートリミット（120 req/min）と指数バックオフリトライ、401 に対するトークン自動リフレッシュをサポート。
    - ページネーション対応のデータ取得関数を実装: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等に保存する関数を実装: save_daily_quotes (raw_prices), save_financial_statements (raw_financials), save_market_calendar (market_calendar) — ON CONFLICT で更新。
    - 型変換ユーティリティ _to_float / _to_int を実装。

- ニュース収集
  - src/kabusys/data/news_collector.py:
    - RSS フィード収集機能の骨組みを実装。記事正規化、URL 正規化（トラッキングパラメータ削除、ソート、フラグメント削除等）、記事ID 生成方針、受信サイズ制限、XML パーサに defusedxml を利用する設計を反映。
    - データベースへのバルク挿入方針、チャンクサイズ制御を含む。

- リサーチ / ファクター計算
  - src/kabusys/research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー系ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の prices_daily / raw_financials を用いた SQL ベースの計算ロジックを提供。日時ウィンドウや欠損値の取り扱いに注意。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（複数ホライズンに対応、範囲限定の最適化あり）。
    - IC 計算（スピアマンランク相関） calc_ic、ランク変換 rank、factor_summary（基本統計量）を実装。
  - src/kabusys/research/__init__.py: 主要関数のエクスポート。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py:
    - research モジュールから得た生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化（zscore_normalize を利用）→ ±3 でクリップ、features テーブルへ日付単位の置換（UPSERT 相当）で保存する build_features を実装。
    - 処理は冪等かつトランザクションで原子性を確保。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して最終スコア final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ保存する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算ロジックを実装（シグモイド変換、欠損補完は中立値0.5）。
    - ウェイトの受け入れ・検証・再スケール処理、Bear レジーム判定（regime_score 平均<0 かつサンプル閾値）、SELL（エグジット）条件（ストップロス・スコア低下）を実装。
    - SELL を優先して BUY から除外するポリシー、トランザクションによる日付単位の置換を採用。

- モジュール公開
  - src/kabusys/strategy/__init__.py: build_features, generate_signals を公開。

### 変更 (Changed)
- （初版のため過去からの変更はなし）各モジュールの設計ドキュメント的コメントをコード内に充実させ、欠損データの扱いやルックアヘッドバイアスへの配慮を明示。

### 修正 (Fixed)
- （初版のため過去からの修正はなし）ただし、トランザクション失敗時に ROLLBACK の失敗をログする防御処理あり。

### セキュリティ (Security)
- news_collector で defusedxml を利用して XML インジェクション / XML Bomb への対策を意識した実装方針を採用。
- ニュース収集において HTTP スキームの検証・SSRF を考慮する方針がコメントで明示（実装の一部は骨組み）。
- API クライアントでのタイムアウト、リトライ、429 の Retry-After 尊重などネットワーク耐性向上の実装。

### ドキュメント / 開発メモ (Notes)
- 多くの関数に設計方針・処理フロー・制約（ルックアヘッドバイアス回避、欠損時の補完方法など）がコメントで記載されており、実運用に向けた注意点が明示されている。
- 期待する DB スキーマ（例: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar, raw_news 等）がコードから推定可能。運用前にスキーマを用意する必要あり。
- 環境変数（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - DB パス: DUCKDB_PATH, SQLITE_PATH
  - 実行環境フラグ: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL
  - 自動 .env ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

### 未実装 / 既知の制約 (Known issues / TODO)
- signal_generator の SELL 条件に記載の一部（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の完全な RSS 取得・パースの実装（ネットワーク取得・ストリーム制限・URL 検査の細部）は骨組み中心。実運用では追加の検証が必要。
- execution モジュール（src/kabusys/execution）は空で、発注ロジック・API 統合は別途実装が必要。
- 一部の入力検証・エッジケース（非常に稀な数値パターン等）はコメントで言及されているが、追加のユニットテスト推奨。

### 互換性 (Compatibility)
- 初回リリースのため下位互換破壊は無し。

---

今後のリリースでは以下を優先予定です:
- execution 層（発注／約定管理）の実装
- news_collector の堅牢な取得ルーチンと記事→銘柄マッピングの実装
- schema migration / 初期テーブル作成ユーティリティの追加
- 詳細なユニットテスト・CI の整備

（以上）