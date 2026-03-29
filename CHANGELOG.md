# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリース (0.1.0) をコードベースから推測して記載しています。

## [Unreleased]

なし

## [0.1.0] - 2026-03-29

### Added
- 初期公開: KabuSys 日本株自動売買システムのコアモジュール群を追加。
  - パッケージ初期化:
    - src/kabusys/__init__.py: __version__ = "0.1.0"、主要サブパッケージを __all__ に公開。
  - 設定・環境変数管理:
    - src/kabusys/config.py:
      - .env/.env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索）。
      - export KEY=val 形式、クォート・エスケープ、インラインコメント処理に対応した .env パーサ実装。
      - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境フラグなどのプロパティ）。
      - 必須環境変数未設定時は ValueError を発生させる _require()。
  - AI ニュース・レジーム判定:
    - src/kabusys/ai/news_nlp.py:
      - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントをスコアリングする score_news() を実装。
      - バッチ処理（1リクエスト最大 20 銘柄）、記事数・文字数トリム、JSON mode 応答パースとバリデーション、±1.0 でクリップ。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装。API キーは引数または OPENAI_API_KEY 環境変数から取得。
      - DuckDB への書き込みは部分失敗に備え、対象コードだけ削除→挿入する冪等処理（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。
      - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（関数を patch できるよう設計）。
    - src/kabusys/ai/regime_detector.py:
      - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、ニュース由来のマクロセンチメント（重み30%）を合成し日次で市場レジーム（bull/neutral/bear）を判定する score_regime() を実装。
      - prices_daily, raw_news, market_regime を参照。マクロセンチメントは OpenAI（gpt-4o-mini）により JSON レスポンスで取得。
      - API エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ、レスポンスの JSON パース失敗も安全に処理。
      - DB 書き込みは冪等（DELETE→INSERT）で行い、トランザクション管理と ROLLBACK の取り扱いあり。
  - 研究 (Research) 機能:
    - src/kabusys/research/factor_research.py:
      - calc_momentum(), calc_volatility(), calc_value() を実装。prices_daily / raw_financials のみ参照し、各種ファクター（モメンタム、MA200乖離、ATR20、出来高・売買代金指標、PER/ROE など）を計算。
      - 欠損やデータ不足に対する None ハンドリング。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns(): 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用）。
      - calc_ic(): スピアマンランク相関（IC）を計算し、計算不能な場合は None を返す。
      - rank(), factor_summary(): ランク付け（同順位は平均ランク）と基本統計量集計を提供。標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py: 主要関数を公開。
    - zscore 正規化ユーティリティは kabusys.data.stats から参照可能（再利用想定）。
  - データ管理 (Data) 機能:
    - src/kabusys/data/calendar_management.py:
      - JPX カレンダー管理 API（market_calendar テーブル）用ユーティリティを実装。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB 登録値を優先し、未登録日は曜日ベース（週末を除く）でフォールバック。探索上限を設けて無限ループを防止。
      - calendar_update_job(): J-Quants クライアントから差分取得し冪等保存、バックフィル・健全性チェックを実装。
    - src/kabusys/data/pipeline.py:
      - ETL パイプライン設計に基づくユーティリティ。差分取得、保存（冪等）、品質チェックフローを想定。
      - ETLResult dataclass を導入（取得件数・保存件数・品質検出・エラー集約・シリアライズ to_dict を含む）。
    - src/kabusys/data/etl.py: pipeline.ETLResult を再エクスポート。
    - DuckDB を主要なローカルデータストアとして利用。DuckDB のバインドの制約（executemany に空リスト不可）に配慮した実装。
  - インターフェースの安定性・テスト配慮:
    - LLM 呼び出し部分は内部関数として抽象化し、テスト時に patch 可能。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接利用しない設計（target_date ベースで処理）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト時に環境変数に依存しないように設計）。
- .env 読み込み時に OS 環境変数を保護する protected フラグを導入し、既存の環境変数が意図せず上書きされないように実装。

### Notes / Implementation details
- OpenAI モデル: gpt-4o-mini をデフォルトで使用。JSON mode を利用して厳密な JSON を期待するが、実装側で前後ノイズを抽出して復元する耐性も持たせている。
- リトライ挙動: 429/ネットワーク/タイムアウト/5xx に対して指数バックオフでリトライ（最大回数は各モジュールで定義）。非 5xx の APIError は再試行せずフォールバックする設計。
- DuckDB トランザクション: AI スコアやレジーム結果の挿入は DELETE→INSERT の形で冪等に保存。DB 書き込み中の例外時には ROLLBACK を試行し、ROLLBACK に失敗した場合は警告ログを出力。
- タイムウィンドウ:
  - news_nlp のニュース集計ウィンドウは JST 基準で「前日 15:00 JST 〜 当日 08:30 JST」を対象（UTC に変換して DB 比較）。
  - regime_detector は prices_daily の date < target_date（排他条件）を満たすデータのみ参照してルックアヘッドを防止。
- DuckDB の日付型処理や互換性に配慮したユーティリティ関数を提供（_to_date 等）。

---

今後のリリースでは、strategy / execution / monitoring サブパッケージの具現化（注文ロジック、実行エンジン、監視/アラート機能）、さらなるテストカバレッジ、ドキュメントの充実を想定しています。