CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- 初回公開リリース。日本株自動売買 / データ基盤向けのユーティリティ群を追加。
- パッケージのメタ情報:
  - kabusys パッケージ初期化（__version__ = "0.1.0", 公開サブパッケージ: data, strategy, execution, monitoring）。
- 環境設定 / ロード:
  - kabusys.config: .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動読み込み。
  - .env / .env.local の読み込み順と上書きルール（OS 環境変数保護、.env.local は override=True）。
  - 柔軟な .env 行パーサ実装（export プレフィックス対応、引用符内エスケープ処理、インラインコメント処理）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスで各種設定プロパティを提供（J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 環境判定など）。必須変数未設定時は明示的に ValueError を送出。
  - 許容される環境値やログレベルのバリデーション実装（例: KABUSYS_ENV, LOG_LEVEL）。
- データ関連:
  - kabusys.data.pipeline: ETLResult データクラスおよび ETL パイプラインの骨格を実装。取得・保存・品質チェックの概念を整理。
  - kabusys.data.etl: ETLResult の再エクスポート。
  - kabusys.data.calendar_management: JPX マーケットカレンダー管理（market_calendar テーブル操作）と営業日判定ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB 優先 → 未登録日は曜日ベースのフォールバック。最大探索日数の上限を設けて無限ループを防止。
    - calendar_update_job: J-Quants から差分取得して冪等的に保存するバッチ処理、バックフィル・健全性チェックを実装。
- 研究（Research）モジュール:
  - kabusys.research.factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離など。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率など。
    - calc_value: PER/ROE の算出（raw_financials から直近財務データを取得）。
    - DuckDB を用いた SQL 主導の計算（外部 API へはアクセスしない設計）。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得する汎用実装（ホライズン検証あり）。
    - calc_ic: スピアマンのランク相関（IC）計算を実装（欠損・重複順位考慮、最小サンプル判定）。
    - rank: 同順位は平均ランクにする実装（丸め処理で ties 検出誤差を抑制）。
    - factor_summary: count/mean/std/min/max/median を返す統計サマリー実装。
- AI / NLP:
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込む。
    - JSTベースのニュースウィンドウ計算（前日 15:00 ～ 当日 08:30 JST を UTC で扱う）を提供（calc_news_window）。
    - バッチ化（1 API コールで最大 20 銘柄）、1 銘柄あたりの記事数/文字数制限、JSON Mode 利用、レスポンス検証およびスコアの ±1.0 クリップ。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、API 例外やパース失敗は警告ログ＋スキップ（フェイルセーフ）。
    - レスポンス前後に余計なテキストが混ざるケースの復元ロジックを実装。
    - テスト可能性のため _call_openai_api を差し替え可能に設計。
  - kabusys.ai.regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を算出・market_regime テーブルへ書き込む。
    - マクロ記事の抽出（キーワードリスト）、OpenAI 呼び出し（gpt-4o-mini、JSON Mode）、再試行ロジック、API 失敗時は macro_sentiment = 0.0 にフォールバック。
    - ルックアヘッドバイアス回避の設計（date 引数ベース・DB クエリで date < target_date を利用）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT と ROLLBACK 保護）。
- 設計上の共通方針（各モジュールに共通）:
  - ルックアヘッドバイアス防止: 内部で datetime.today()/date.today() を参照しない設計（target_date を明示的に渡す）。
  - DuckDB をデータ層に利用（SQL と Python の組合せで処理）。
  - API 呼び出し失敗時は例外で完全停止させず、ロギングしてフォールバックするフェイルセーフ設計。
  - テスト容易性を考慮し、API 呼び出しや時間に依存する内部関数の差し替えを想定した実装。

Changed
- （初回リリースのため過去変更なし）

Fixed
- （初回リリースのため過去修正なし）

Security
- 環境変数の取り扱いに注意:
  - 必須 API キー（OPENAI_API_KEY 等）が未設定の場合は明示的な ValueError を発生させるため、運用時は適切に環境変数を注入する必要があります。
  - .env 自動読み込み時に OS 環境変数は保護され、.env の内容で上書きされない設計（ただし .env.local は override=True の挙動に注意）。

Notes / Limitations / Known issues
- DuckDB の executemany に空リストを渡せない制約を考慮した実装（空の params を事前にチェック）。
- OpenAI の JSON Mode でも稀に前後テキストが混入する実装上の想定があるため、レスポンス復元ロジックを実装しているが完璧ではない可能性がある。
- kabusys.monitoring / strategy / execution の公開は __all__ に含まれるが、この CHANGELOG に示した範囲以外の詳細実装は省略（該当モジュールはパッケージ構成として存在）。
- 一部のパラメータ（バッチサイズ、モデル名、閾値など）は定数としてソース内にハードコードされている（今後設定化の余地あり）。

Acknowledgements
- このリリースは DuckDB と OpenAI API を中心に設計。設計方針として「データ品質重視」「ルックアヘッドバイアス回避」「冪等性」「テスト容易性」を重視しています。