KEEP A CHANGELOG
=================

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。
https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース。パッケージ名: kabusys、目的: 日本株自動売買システムのコアライブラリを提供。
  - パッケージ初期化:
    - src/kabusys/__init__.py にてバージョン "0.1.0"、公開 API 群 (data, strategy, execution, monitoring) を定義。
  - 設定・環境変数管理:
    - src/kabusys/config.py
      - .env / .env.local の自動ロード機能（プロジェクトルートを .git または pyproject.toml で探索）。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
      - .env パースの堅牢化 (_parse_env_line): `export ` プレフィックス対応、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等。
      - _load_env_file による保護済みキー（既存 OS 環境変数）を上書きしない挙動や override オプション。
      - Settings クラスで使用するプロパティ群（J-Quants トークン、KabuAPI 設定、Slack トークン・チャンネル、DB パス、環境種別・ログレベル検証など）。
  - データ取得・保存（J-Quants API クライアント）:
    - src/kabusys/data/jquants_client.py
      - API へのリクエスト共通実装 (_request):
        - 固定間隔スロットリングによるレート制御（120 req/min を想定、_RateLimiter）。
        - 再試行（指数バックオフ、最大 3 回）、HTTP 408/429/5xx のリトライ処理。
        - 401 受信時の自動トークンリフレッシュ（get_id_token を呼び 1 回リトライ）。
        - ページネーション対応（pagination_key）。
        - JSON デコード時のエラーハンドリング。
      - 認証ヘルパー: get_id_token（リフレッシュトークンから ID トークン取得）。
      - データ取得関数:
        - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応、ログ出力）。
      - DuckDB への冪等保存関数:
        - save_daily_quotes: raw_prices へ ON CONFLICT DO UPDATE により upsert。
        - save_financial_statements: raw_financials へ upsert（PK: code, report_date, period_type）。
        - save_market_calendar: market_calendar へ upsert。
      - データ変換ユーティリティ: _to_float / _to_int（安全な型変換。空値・不正値は None）。
      - データ取得時に fetched_at を UTC 時刻で記録（Look-ahead バイアスのトレースを容易に）。
      - モジュールレベルの ID トークンキャッシュを実装（ページネーション等で共有）。
  - ニュース収集:
    - src/kabusys/data/news_collector.py
      - RSS フィード収集の基礎実装（既定ソース: Yahoo Finance のビジネス RSS）。
      - defusedxml を使った XML パース（XML Bomb 等の脅威緩和）。
      - 受信バイト上限 (MAX_RESPONSE_BYTES = 10 MB) によるメモリ DoS 対策。
      - URL 正規化 (_normalize_url): トラッキングパラメータ除去(utm_ 等)、スキーム/ホスト小文字化、フラグメント削除、クエリソート。
      - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
      - HTTP スキーム検証・SSRF 緩和のためのホスト/スキーム制約（実装方針）。
      - raw_news への冪等保存（ON CONFLICT DO NOTHING 想定）、news_symbols で銘柄紐付け（設計方針）。
      - DB 書き込みをバルクチャンク化してオーバーヘッドを削減。
  - 研究（Research）モジュール:
    - src/kabusys/research/factor_research.py
      - モメンタム: calc_momentum（mom_1m, mom_3m, mom_6m, ma200_dev）。200日 MA のデータ不足は None を返す。
      - ボラティリティ/流動性: calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）。ATR のデータ不足は None。
      - バリュー: calc_value（per, roe）、raw_financials の最新報告を参照。
      - SQL とウィンドウ関数を用いた効率的実装（DuckDB 前提）。営業日欠損に対するスキャンバッファ設計あり。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算: calc_forward_returns（複数ホライズン対応、営業日ベースのラグ取得）。
      - IC（Information Coefficient）計算: calc_ic（Spearman の ρ をランクで算出、サンプル数閾値あり）。
      - ランク変換ユーティリティ: rank（同順位は平均ランク、浮動小数丸め対策あり）。
      - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
    - src/kabusys/research/__init__.py にて公開 API を整理。
  - 特徴量エンジニアリング・戦略:
    - src/kabusys/strategy/feature_engineering.py
      - research モジュールから生ファクターを取得後、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
      - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 にクリップして外れ値影響を抑制。
      - features テーブルへ日付単位で置換（DELETE+INSERT のトランザクションで原子性確保）。戻り値は upsert した銘柄数。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合し、component（momentum/value/volatility/liquidity/news）ごとのスコアを計算。
      - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
      - 重み付け合算による final_score の算出（デフォルト重みを定義）。ユーザー指定 weights を検証・正規化して適用。
      - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）。Bear 時は BUY を抑制。
      - BUY 閾値デフォルト 0.60。BUY と SELL（エグジット条件: ストップロス -8% / スコア低下）を生成。
      - SELL を優先し、signals テーブルへ日付単位で置換（トランザクション）。
      - 不適切な weights 指定時は警告ログでスキップ・フォールバック。
  - パッケージ構成:
    - strategy パッケージは build_features / generate_signals を公開。
    - execution パッケージの __init__ を設置（将来的な発注層のためのプレースホルダ）。
    - monitoring は公開対象に含むが、本差分では実装詳細は含まれない。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- defusedxml を用いた RSS パースで XML 関連の脆弱性軽減。
- ネットワーク関係でのリトライ時に Retry-After ヘッダを尊重（429 の場合）。

Notes / Known limitations
- 一部の戦略的エグジット条件は未実装:
  - トレーリングストップ（peak_price を用いた -10% 判定）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）も未実装。
- feature_engineering / factor_research の一部出力はデータ欠損時に None を返す（MA200 等のウィンドウ要件）。
- news_collector の詳細な外部ネットワーク制限（IP/ホストフィルタ等）は設計方針として記載済みだが、本差分での厳密な実装は限定的。
- execution パッケージは現時点で発注ロジックを有していない（プレースホルダ）。
- DB スキーマ（テーブル名・カラム名）は実装側で暗黙の前提があるため、導入時はスキーマ整備が必要（例: raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等）。

導入・移行メモ
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings で _require によって確認）。
  - 任意: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_DISABLE_AUTO_ENV_LOAD。
- DuckDB 接続は各関数に対して外部から渡す設計（テストやバッチ処理で容易に差し替え可）。
- J-Quants API 利用時はレート制限・認証トークン有効期限に注意。モジュールは自動リフレッシュとリトライを備えるが、運用上のモニタリングを推奨。

Contact
- 本 CHANGELOG はソースコード内の実装とドキュメント文字列（docstring）から生成されました。実際の運用や拡張に際してはソースを参照してください。