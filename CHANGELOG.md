# Changelog

すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  

[Unreleased]

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0" として公開。
  - 公開サブパッケージ: data, research, ai, など（__all__ に data, strategy, execution, monitoring を指定）。

- 環境・設定管理モジュール（kabusys.config）
  - .env ファイル／環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に探索（カレントワーキングディレクトリに依存しない挙動）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用フック）。
    - 読み込み優先度: OS 環境変数 > .env.local > .env。既存 OS 環境変数は保護され上書きされない。
  - .env パーサーの堅牢化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理。
    - クォートなしのコメント処理（'#' の扱い）に細かいルールを実装。
    - 読み込み失敗時は警告を出力して続行。
  - Settings クラスを提供（settings = Settings()）。主要プロパティ:
    - J-Quants / kabuステーション / LINE API 関連のキー取得。
    - データベースパス（DuckDB / SQLite）、監視用ファイルパス（PID / kill flag）等の Path 返却。
    - CPU/メモリ/ディスク閾値、環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション（有効値のチェック）。
    - is_live / is_paper / is_dev のブール判定ユーティリティ。
  - 必須値取得ヘルパー _require は未設定時に ValueError を発生させる。

- AI（自然言語処理）モジュール
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を用いて銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime に変換）。
    - 銘柄ごとに最新各種記事を集約し、トークン肥大化対策（最大記事数・最大文字数トリム）を実装。
    - バッチ処理: 1 API コールあたり最大 _BATCH_SIZE (20) 銘柄単位で送信。
    - 再試行ポリシー: 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
    - レスポンス検証: JSON 抽出、"results" 構造・型チェック、未知コードの無視、スコアの数値変換と有限性チェック。
    - スコアは ±1.0 にクリップ。書き込みは ai_scores テーブルへ、取得できたコードのみ DELETE→INSERT で置換（部分失敗時に既存スコアを保護）。
    - テスト容易性: _call_openai_api をモック差替え可能。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（'bull' / 'neutral' / 'bear'）。
    - ma200_ratio の計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロニュース抽出はキーワードベース（定義済みの _MACRO_KEYWORDS）でタイトルを取得し、LLM（gpt-4o-mini, JSON Mode）で -1.0～1.0 にスコア化。
    - API エラー時は macro_sentiment=0.0 とするフェイルセーフ設計。API 呼び出しは独立実装でモジュール結合を避ける。
    - レジームスコアは定数スケール・閾値でラベル化し、市場レジームは market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。

- Research（リサーチ）モジュール
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 約1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を含むモメンタム指標を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率などを計算。部分窓は考慮しつつ必要行数チェック。
    - calc_value: raw_financials から最終財務データと価格を組み合わせて PER / ROE を算出。EPS が 0/欠損時は None。
    - すべて DuckDB の SQL を活用し、外部 API へはアクセスしない（研究環境向け）。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。horizons の検証（1..252）を実施。
    - calc_ic: スピアマンランク相関により IC を算出（有効レコード 3 件未満は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を提供。
    - 実装は標準ライブラリのみで pandas 等に依存しない。

- Data（データ基盤）モジュール
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を基に営業日判定・前後営業日探索・期間内営業日取得・SQ判定を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日（平日）ベースでフォールバックする一貫した挙動。
    - 探索は最大 _MAX_SEARCH_DAYS（保護）で上限ガード。カレンダー更新ジョブ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors など）。
    - ETL の設計方針: 差分更新、バックフィル、品質チェックの収集（Fail-Fast しない）などを明記。
    - internal ユーティリティ: テーブル存在チェック、最大日付取得等（DuckDB 前提）。

Changed
- （初回リリースのため「変更」はなし。設計上の重要ポイント・決定事項をドキュメントに明記）
  - すべての「日付」関連処理は date / UTC naive datetime で統一し、datetime.today() / date.today() の直接参照によるルックアヘッドバイアスを避ける設計方針を採用。
  - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの堅牢なパースとバリデーションを実装。

Fixed
- （初回リリースのため「修正」はなし）

Security
- 環境変数ロード時に既存の OS 環境変数を保護する仕組みを導入（.env による上書きを防ぐ protected set）。

Notes / Internal
- テスト支援のため、OpenAI 呼び出し部分（各モジュールの _call_openai_api）を unittest.mock.patch 等で差し替え可能にしている。
- DuckDB をデータレイヤーの主要ストレージとして想定しているため、SQL レベルでの互換性（executemany の挙動など）を考慮した実装が多数ある。
- 一部モジュール（execution, monitoring, strategy 等）は __all__ に含まれているが、ここで提供されたコード断片では詳細実装は含まれていない（今後追加予定）。

もし CHANGELOG に追記したい項目（リリース日や項目の表記方法の調整、より技術的な差分の追記）があれば教えてください。必要に応じて英語版やリリースノートの簡潔版も作成します。