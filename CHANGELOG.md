CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
--------------------

Added
- 初回リリース。本パッケージ "kabusys" を追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py による公開 API の定義（data, research, ai, ... を想定）。
    - バージョン: 0.1.0

- 環境変数・設定管理:
  - src/kabusys/config.py を追加。
    - .env ファイルまたは環境変数から設定値を読み込み。
    - プロジェクトルート検出: .git または pyproject.toml を基準に探索する _find_project_root を実装（CWD 非依存）。
    - .env パーサ: _parse_env_line により export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント判定などをサポート。
    - .env 自動読み込みの優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - _load_env_file: protected 引数で OS 環境変数を保護しつつ上書き制御。
    - Settings クラスを提供（settings インスタンスをエクスポート）。
      - J-Quants / kabuAPI / LINE / データベースパス（duckdb, sqlite） / 監視用ファイルパス・閾値 / システム環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）等のプロパティを定義。
      - KABUSYS_ENV と LOG_LEVEL 値検証（許容値以外は ValueError を送出）。
      - パスは Path.expanduser() で扱う。

- AI 関連:
  - src/kabusys/ai/news_nlp.py を追加。
    - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ計算（calc_news_window）: JST 基準で前日 15:00 ～ 当日 08:30 を対象（UTC に変換）。
    - バッチ処理: 1 回の API 呼び出しで最大 20 銘柄（_BATCH_SIZE）、1 銘柄あたり記事数・文字数上限を設けトリム。
    - OpenAI JSON Mode を利用、レスポンスの厳格バリデーション（JSON 抽出、results 配列、code/score チェック、スコアの ±1.0 クリップ）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx は指数バックオフでリトライ、その他はスキップ。部分失敗時は他銘柄スコアを保護するため DELETE → INSERT の方式で差分置換。
    - テスト容易性: _call_openai_api の差し替え・patch を想定。
    - ロギング: 対象記事なし・失敗時の情報を詳細にログ出力。
  - src/kabusys/ai/regime_detector.py を追加。
    - 日次の市場レジーム判定（score_regime）を実装。
    - 1321（日経225連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して regime_score を算出し、market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を使用。API 失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - MA 計算は target_date 未満のデータのみ参照しルックアヘッドを防止。
    - リトライ/バックオフ・API エラーのハンドリングを実装。
    - テストのため _call_openai_api の差し替えポイントを用意。
    - 設定: 重み・閾値・キーワードリスト・最大記事数等を定数化。

- Research（因子・特徴量探索）:
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（calc_momentum）、ボラティリティ/流動性（calc_volatility）、バリュー（calc_value）ファクターを実装。
    - DuckDB 上の prices_daily / raw_financials を参照し、(date, code) をキーとする dict リストを返す設計。
    - 計算上のデータ不足や条件不成立時は None を返す（安全設計）。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank ユーティリティ、factor_summary（統計要約）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。rank は同順位を平均ランクで処理。
  - src/kabusys/research/__init__.py で主要関数を再エクスポート（zscore_normalize は data.stats 由来）。

- Data / ETL / カレンダー:
  - src/kabusys/data/calendar_management.py を追加。
    - JPX マーケットカレンダー管理機能を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。market_calendar が無ければ曜日ベースでフォールバック。
    - calendar_update_job により J-Quants API から差分取得して market_calendar を冪等保存（バックフィル・健全性チェックを含む）。
    - DuckDB の日付型取り扱い補助や最大探索日数などの安全策を実装。
  - src/kabusys/data/pipeline.py を追加。
    - ETLResult dataclass により ETL の結果（取得数・保存数・品質問題・エラー等）を格納可能に。
    - ETL の設計方針（差分更新、バックフィル、品質チェックの扱い）を実装方針として明記。
    - DuckDB 互換性考慮（executemany に空リストを与えない等）を考慮。
  - src/kabusys/data/etl.py で ETLResult を再エクスポート。

- テスト支援・設計方針:
  - 多くのモジュールで外部 API 呼び出し（OpenAI / J-Quants）を差し替え可能に実装し、ユニットテストを容易化。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る実装）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / 実装上の注意
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を利用するため、API 形式や SDK のバージョン依存に注意。モジュール内で status_code 取得等に柔軟性を持たせている。
- DB 書き込みは基本的にトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等に行う。例外発生時は ROLLBACK を試みログ出力。
- AI スコアの部分失敗時は既存スコアを保護するため、書き込み対象コードを絞って置換する実装。
- DuckDB の executemany の挙動（空リスト不可等）に対する対策を各所で実装済み。
- 環境変数の自動読み込みはプロジェクトルート検出に依存するため、配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用するか明示的に環境変数を設定することが推奨される。

---
この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートや利用方法については README やドキュメントを参照してください。