CHANGELOG
=========

この CHANGELOG は「Keep a Changelog」準拠の形式で、コードベース（kabusys）の現在の状態から推測して作成しています。
バージョン番号はパッケージ内の __version__ に合わせています。

Unreleased
----------

（無し）

[0.1.0] - 2026-04-03
--------------------

Added
-----
- パッケージ初期リリース (kabusys v0.1.0)
  - 日本株自動売買システムのコア機能群を実装。
  - パブリック API として以下のサブパッケージ/モジュールを提供:
    - kabusys.config: 環境変数 / .env 管理（自動ロード機能含む）
    - kabusys.ai: ニュース NLP と市場レジーム判定
    - kabusys.data: データ ETL、カレンダー管理、パイプライン補助
    - kabusys.research: ファクター計算・特徴量解析
    - kabusys.research.*: ファクター研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等）
  - パッケージメタ情報: __version__ = "0.1.0"、主要 export を __all__ に定義。

- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルートを .git または pyproject.toml により検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
  - .env ファイルパーサ実装:
    - export KEY=val 形式対応、シングル／ダブルクォート処理（バックスラッシュエスケープ考慮）、行コメント処理。
  - 環境変数保護ロジック（OS 環境変数は protected として上書き抑止）をサポート。
  - Settings クラスを提供し、キーごとの取得プロパティを公開（必須項目は _require により ValueError を送出）。
  - デフォルト値を備えた設定（KABU_API_BASE_URL、DB パス、PID/KILL フラグパス、監視閾値など）。
  - 設定値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェック。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントを取得。
  - バッチ処理（1 API コールにつき最大 20 銘柄）・記事数 / 文字数トリム機能（1銘柄あたり最大記事数/最大文字数）。
  - 再試行ポリシー: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ。
  - レスポンスの厳密バリデーション（JSON 抽出、results 配列、code/score の検証、スコアの浮動小数チェック）。
  - スコアは ±1.0 にクリップし、ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込み。
  - ルックアヘッドバイアス防止の設計: 内部で date.today() を参照せず、target_date パラメータでウィンドウを決定。
  - テスト容易性: OpenAI 呼び出し箇所を差し替え可能（_call_openai_api を patch 可能）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）判定。
  - prices_daily と raw_news を参照し、calc_news_window を利用した安全な時間窓でニュースを取得。
  - OpenAI を用いたマクロセンチメント評価（_MODEL=gpt-4o-mini、JSON mode）。
  - API エラー時のフェイルセーフ: macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
  - 計算結果を market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時ROLLBACK処理）。
  - 再試行 / エラーハンドリング、ログ出力を充実。

- データ (ETL / Pipeline / Calendar)（kabusys.data.*）
  - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を ETL の結果表現として再エクスポート）。
    - ETL の取得件数、保存件数、品質問題、エラー一覧などを保持。ヘルパー to_dict を提供。
  - pipeline モジュール: 差分取得・保存・品質チェックのための基盤。J-Quants クライアント（jq）を利用した idempotent 保存方針を採用。
  - calendar_management:
    - market_calendar を基にした営業日判定 API（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先 -> 未登録日は曜日ベース（週末非営業）でフォールバックする一貫した振る舞い。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新（バックフィル、健全性チェックを実装）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) を導入し無限ループを防止。
  - DuckDB を第一選択のストレージとして想定（関数は DuckDB の接続オブジェクトを引数に取る）。

- 研究 / ファクター計算（kabusys.research.*）
  - ファクター計算モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、ma200 乖離（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率（データ不足は None）。
    - calc_value: PER（EPS=0/欠損は None）、ROE（raw_financials の最新データを使用）。
  - 特徴量探索 / 統計ユーティリティ:
    - calc_forward_returns: 指定ホライズンの将来リターン（一度に複数ホライズンを取得可能、horizons バリデーションあり）。
    - calc_ic: スピアマン（ランク）相関で IC を計算（有効レコード < 3 なら None）。
    - rank: 同順位は平均ランクで処理（丸めによる ties の検出対策あり）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - DuckDB と標準ライブラリのみ依存（pandas 等に依存しない実装）。

Changed
-------
- 初回リリースのため、既存コードに対する互換性変更は無し。

Fixed
-----
- 初回リリースのため、バグ修正履歴は無し（ただし各モジュールで堅牢性・フェイルセーフを重視した実装を採用）。

Security
--------
- OpenAI API キーや各種シークレットは環境変数で管理（Settings が必須キーに対して ValueError を投げる）。
- .env ファイル読み込み時には OS 環境変数を保護する仕組みを実装。

Notes / Known Limitations
-------------------------
- OpenAI / J-Quants / kabu ステーション等外部 API クライアントは実装はあるが、実運用では各 API キー・ネットワーク設定が必要。
- news_nlp と regime_detector は gpt-4o-mini（JSON Mode）を前提にしているため、モデル仕様の変更で調整が必要になる可能性がある。
- calc_value: PBR・配当利回りは未実装（将来拡張予定）。
- DuckDB バインドの互換性（executemany に空リスト不可等）を考慮した実装を行っているが、使用する DuckDB のバージョン依存の注意点あり。
- 一部の内部ユーティリティ（例: jquants_client）の実装はこのコードベースに含まれていないため、実行には外部モジュールの提供が必要。

移行・運用メモ
--------------
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - OPENAI_API_KEY（AI 機能を使用する場合）
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 監視用の PID / KILL フラグ関連の設定有り（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）。
- 実運用では KABUSYS_ENV を "development" / "paper_trading" / "live" のいずれかに設定すること。値が不正な場合は起動時に例外となる。

ライセンス / 著作権
-------------------
- この CHANGELOG はコード構成とソースコメントから推測して作成しています。実際の CHANGELOG/リリースノートはリリース時に適宜編集してください。