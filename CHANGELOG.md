CHANGELOG
=========

すべての注目すべき変更をこのファイルに記載します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。  

フォーマット:
- Added: 新機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

[Unreleased]
-------------

- 今後の変更点や作業中の内容をここに記載してください。

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース。
- 環境変数・設定管理モジュールを追加（kabusys.config）。
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - 必須環境変数取得ヘルパ _require と環境値の検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
  - 設定のユーティリティプロパティ群（API トークン/URL、DB パス、監視閾値、PID/kill ファイルパス、paper trading 関連設定など）。

- ポートフォリオ構築関連モジュールを追加（kabusys.portfolio）。
  - 銘柄選定: select_candidates — スコア降順での候補選定（同点時のタイブレークロジック含む）。
  - 重み計算: calc_equal_weights（等配分）、calc_score_weights（スコア加重、全スコア0の際は等配分へフォールバック）。
  - リスク調整: apply_sector_cap（セクター集中の上限チェック。既存保有のエクスポージャー集計、売却予定銘柄の除外に対応）、calc_regime_multiplier（市場レジームに応じた投下資金乗数）。
  - ポジションサイズ決定: calc_position_sizes（risk_based / equal / score の割当方式、単元株丸め、per-position/aggregate の上限、コストバッファ考慮、スケールダウン＆切捨て後の端数配分アルゴリズム）。

- リサーチ / ファクター計算モジュールを追加（kabusys.research）。
  - ファクター計算: calc_momentum（1/3/6ヶ月リターン、MA200乖離）、calc_volatility（ATR20、相対ATR、20日平均売買代金、出来高比率）、calc_value（PER/ROE の算出）。
  - 特徴量探索: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関での IC 計算）、factor_summary（各ファクターの基本統計量）、rank（同順位は平均ランク）。
  - 設計方針: DuckDB に接続して prices_daily / raw_financials を参照、外部 API 呼び出しなし、純粋関数群として実装。

- AI 関連モジュールを追加（kabusys.ai）。
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書込む。
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ。
    - バッチ処理（最大 _BATCH_SIZE=20）、1銘柄あたりの記事数/文字数上限によるトリム、API の再試行（指数バックオフ、429/ネットワーク/5xx に対応）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列・型チェック、未知コードの無視、スコアの数値変換と有限性チェック）。
    - スコアは ±1.0 にクリップ、部分成功時に既存スコアを保護しつつ対象コードのみ DELETE→INSERT。
    - テスト用に OpenAI 呼び出し部分を差し替え可能（_call_openai_api を patch 可）。
  - レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' を判断。
    - マクロキーワードによる raw_news 抽出、最大記事数制限、OpenAI 呼び出しの再試行、API 失敗時は macro_sentiment=0.0 でフォールバック。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）。テスト用に API 呼び出し箇所を差し替え可能。

- 監視ログ永続化層を追加（kabusys.monitoring.monitoring_db）。
  - SQLite を用いた永続化。system_status, trade_logs, positions, risk_logs 等のテーブル作成（冪等な init_monitoring_db を提供）とインデックス作成。

- パッケージ初期化情報（kabusys.__init__.py）にバージョン "0.1.0" と公開モジュール一覧を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数に依存する API キー類は明示的に引数で注入可能にし、未設定時は例外を投げることで安全な失敗（フェイルセーフ）を実現（OpenAI キーなど）。

Notes / Known limitations / TODO
- .env 読み込み:
  - プロジェクトルート検出に失敗すると自動ロードをスキップする設計（配布後の動作を意識）。
- sector exposure の価格欠損:
  - apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過小評価される可能性がある旨の TODO 注記。将来的には前日終値や取得原価でフォールバックすることを検討。
- 単元株情報:
  - 現状は全銘柄共通の lot_size（デフォルト 100）を想定。将来的に銘柄別の lot_map をサポートする余地あり（TODO 記載）。
- AI モジュール:
  - LLM の出力が期待フォーマットを逸脱した場合に備え、可能な限り堅牢にパース・フォールバックするが、誤った解析結果は起こり得る（ログに警告を出力してスキップ／フォールバック）。
- DuckDB executemany:
  - DuckDB のバージョン差異により executemany に空リストを渡せない制約に対応するため、空チェックを行っている。

作者備考
- 各モジュールは「外部副作用を最小化する」方針で設計されています（DuckDB / SQLite 以外のネットワーク呼び出しは明示的に切り替え可能、datetime.today() 等の直接参照を避けることでルックアヘッドバイアスを防止）。
- 単体テストの容易さを意識して、外部 API 呼び出し箇所は差し替え可能にしてあります（テスト時に patch して制御可能）。

---
この CHANGELOG はコードベース（src/ 以下）の実装内容から推測して作成しています。必要に応じて日付、カテゴリの調整や追加の変更履歴を追記してください。