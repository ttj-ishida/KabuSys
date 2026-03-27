Keep a Changelog
=================

すべての変更は https://keepachangelog.com/ja/ に準拠しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0
- パッケージ公開インターフェースを追加
  - src/kabusys/__init__.py で data, strategy, execution, monitoring を公開。
  - src/kabusys/ai/__init__.py で score_news を公開。
  - src/kabusys/research/__init__.py で研究用ユーティリティとファクター計算関数を公開。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。
- 環境変数・設定管理
  - src/kabusys/config.py を追加。
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理などに対応。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須キー取得時の _require() による明示的エラー（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - ログレベル・環境（development / paper_trading / live）検証、Path デフォルト値（DUCKDB_PATH, SQLITE_PATH）の提供。
  - settings オブジェクトで is_live / is_paper / is_dev プロパティを提供。
- AI（ニュース NLP / レジーム判定）
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を集約して銘柄ごとにニュースを統合し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄別センチメント（-1.0〜1.0）を算出。
    - バッチ処理（最大20銘柄／チャンク）、トークン肥大化対策（記事数/文字数制限）、レスポンス検証・クリッピング、部分成功時に既存スコアを保護する idempotent な DB 更新（DELETE → INSERT）。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを組み込み、失敗時はスキップしてフェイルセーフを保持。
    - テスト用に _call_openai_api の差し替えが可能。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321（日経225連動型）の直近200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロキーワードによる記事抽出、OpenAI 呼び出しのリトライ・フォールバック（失敗時 macro_sentiment=0.0）。
    - レジーム算出ロジックと閾値の定義（BULL/BEAR閾値、スコアクリップ等）。
- Data（ETL / カレンダー / パイプライン）
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理: market_calendar テーブルを用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB に登録がない場合は曜日ベースでフォールバック（土日非営業日）。
    - calendar_update_job により J-Quants API からの差分取得・バックフィル（直近日数再取得）・健全性チェックを実装。
  - src/kabusys/data/pipeline.py
    - ETL パイプラインの土台（差分更新、idempotent 保存、品質チェックの集約）。
    - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラー一覧、ヘルパーメソッド to_dict / has_errors / has_quality_errors）。
    - DuckDB を前提とした最大日付取得やテーブル存在チェックのユーティリティを提供。
    - 初期データ取得用の最小日付定義やバックフィルポリシーを定義。
  - DuckDB 関連の実装上の配慮
    - executemany に空リストを渡せない（DuckDB 0.10 の制約）ため、空時は実行しない保護処理を追加。
    - 日付の取り扱いを date オブジェクトで統一し timezone 混入を防止。
- Research（ファクター計算・特徴量探索）
  - src/kabusys/research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン・200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR（true range の扱いを厳密に）、相対 ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得し PER/ROE を計算（未実装の指標は注記）。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API を呼ばない設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを一括クエリで取得（範囲バッファを持つ）。
    - calc_ic: Spearman（ランク）による IC（Information Coefficient）計算（必要件数チェック、欠損除外）。
    - rank: 同順位は平均ランクで処理（丸めで ties を検出）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー。
    - pandas 等外部ライブラリに依存せず純標準ライブラリで実装。
- 設計ポリシーの明示
  - ルックアヘッドバイアス防止のため、各種処理は datetime.today()/date.today() を内部で参照せず、target_date を明示的に受け取る設計。
  - API 呼び出し失敗時は例外を即座に投げずフェイルセーフ（ゼロやスキップ）で続行する箇所を多数実装。
  - ロギングを多用して内部状態・警告・リトライ情報を出力。

Changed
- （初回リリースのため該当なし）

Fixed
- 初期実装段階での堅牢化
  - .env 読み込み時のファイルアクセス失敗を警告化して処理継続する（warnings.warn）。
  - DuckDB の日付取り扱いや NULL 値・データ不足時の挙動を明示（例: ma200 データ不足時は中立値を使用）。
  - OpenAI API レスポンスの JSON パース失敗や予期しない構造に対して安全にハンドリング（ログ出力後フェイルセーフ値にフォールバック）。

Security
- API キー・トークンは環境変数経由で取得する設計（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN 等）。コード内にハードコードされた秘密は含まれないよう設計。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 開発者向けメモ
- テストしやすさ
  - OpenAI 呼び出し部分は _call_openai_api を unittest.mock.patch で差し替え可能にしており、外部 API への依存をテストから切り離しやすくなっている。
  - 環境変数自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで無効化でき、CI/テスト環境での副作用を抑制できる。
- DuckDB バージョン互換性
  - executemany の空リストバインド制約を考慮した実装を行っている（DuckDB 0.10 を念頭に置いた互換性処理）。
- 将来の拡張候補
  - news_nlp / regime_detector の LLM モデル切替やプロンプト改善。
  - バックテスト・実運用の strategy / execution モジュールの追加実装（公開インターフェースは既に用意）。

-----------

作者: kabusys 開発チーム
