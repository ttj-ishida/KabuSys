CHANGELOG
=========

すべての変更は Keep a Changelog に準拠して記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-27
-------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。
  - バージョン: 0.1.0

- 環境設定/設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - プロジェクトルートは .git または pyproject.toml を起点に検出（CWD 非依存）。
  - .env ファイルパーサを実装（クォート文字、バックスラッシュエスケープ、export プレフィックス、インラインコメント等に対応）。
  - 環境変数保護機能（既存 OS 環境変数を保護する protected set）を導入。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを公開。
    - 必須項目未設定時は ValueError を送出する挙動を明示。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
    - is_live / is_paper / is_dev ヘルパを追加。

- AI モジュール（src/kabusys/ai ディレクトリ）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini / JSON mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を計算。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を JST→UTC に変換して DB 比較に使用（calc_news_window を提供）。
    - バッチ処理: 1 API コールで最大 20 銘柄（_BATCH_SIZE）。
    - 1 銘柄あたり最大記事数・最大文字数でトリム（過トークン対策）。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフでリトライ。
    - レスポンス検証: JSON パース、"results" の存在、code/score の型検証、未知コードは無視、スコアを ±1.0 にクリップ。
    - DB への保存は部分失敗に強い設計（取得できた code のみ DELETE → INSERT）およびトランザクション管理（BEGIN/ROLLBACK/COMMIT）。
    - テストしやすい設計: OpenAI 呼び出し部分は _call_openai_api をパッチ差し替え可能。
    - 失敗時はフェイルセーフでスキップし処理継続（例外を投げずログで通知）。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を組み合わせて市場レジーム（bull / neutral / bear）を日次判定。
    - ma200_ratio 計算は target_date 未満のデータのみ使用し、ルックアヘッドバイアスを防止。
    - マクロニュース抽出はマクロキーワード群でフィルタ（最大 20 件）し、LLM（gpt-4o-mini）で -1.0～1.0 のスコアを取得。
    - 合成スコアはクリップされ、閾値に基づいてラベル付与。
    - DB 書き込みは冪等（DELETE → INSERT をトランザクション内で実行）。
    - API エラーやパースエラー発生時は macro_sentiment=0.0 にフォールバックして継続するフェイルセーフ設計。
    - OpenAI 呼び出し部分は _call_openai_api をパッチ差し替え可能。

- Data / ETL / カレンダー管理（src/kabusys/data ディレクトリ）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルをベースに JPX カレンダー（祝日・半日取引・SQ日）を扱うユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - DB にカレンダーがない場合は曜日ベースのフォールバック（土日を非営業日扱い）。
    - next/prev_trading_day や get_trading_days は DB 登録値を優先し未登録日は曜日フォールバックで一貫した挙動。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants から差分取得して ON CONFLICT で上書き。バックフィル・健全性チェックあり（最大未来日数チェック）。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL の差分取得、保存、品質チェックのための基盤実装。
    - ETLResult dataclass を導入し、取得数・保存数・品質問題・発生エラーを集約して返却。
    - テーブル存在チェック、最大日付取得ユーティリティを提供。
    - デフォルトのバックフィル日数 / 最小データ日などの定数を定義。
    - jquants_client（外部モジュール）との連携を想定した設計。
    - 部分失敗時の保護や DuckDB の executemany 空リスト制約に配慮した実装。

- Research（src/kabusys/research ディレクトリ）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。欠損制御あり。
    - calc_value: raw_financials から最新財務データを取得して PER（EPS が有効な場合）/ ROE を計算。
    - DuckDB の SQL ウィンドウ関数を活用した高速集約実装。外部 API にアクセスしない安全設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定基準日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。引数バリデーションあり（horizons は 1..252）。
    - calc_ic: Spearman（ランク相関）に基づく Information Coefficient を計算。必要レコード数が不足する場合は None を返す。
    - rank: 同順位は平均ランクを返すランク変換ユーティリティ（round(..., 12) による tie 安定化）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を返す統計サマリー。

- テスト容易性・設計上の配慮
  - OpenAI 呼び出し箇所は内部関数（_kabusys.ai.*._call_openai_api）をパッチして差し替え可能にしており、ユニットテストでモックしやすい設計。
  - datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）を多くの処理で採用。
  - API 失敗時のフェイルセーフ（例: スコア 0.0 にフォールバック、スキップ継続）を明確化。
  - DuckDB を想定した SQL 実装および互換性配慮（ex. executemany 空リスト回避）。

Security
- OpenAI API キーは関数引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を発生させるため誤操作を防止。

Dependencies
- duckdb（データ処理およびクエリ）
- openai（OpenAI SDK）を使用する前提。API エラー種別に応じたリトライロジックを実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / Known limitations
- jquants_client の実装は本差分内では参照されるが（calendar/pipeline から）、本 CHANGELOG 作成時点での外部依存実装に依存します。
- 一部の公開 API（monitoring, execution, strategy 等）は __all__ に名前が含まれていますが、本差分のファイル一覧には含まれていません（今後のリリースで追加予定）。
- DuckDB バインド/バージョン差異に起因する挙動（例: list 型バインドの取り扱い）に配慮した実装を行っていますが、環境依存の微調整が必要となる場合があります。