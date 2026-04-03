# Changelog

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog の規約に従います。
なお日付はリリース日を表します。

## [Unreleased]
- 今後の変更・計画をここに記述します。

## [0.1.0] - 2026-04-03
初回リリース。日本株自動売買システム「KabuSys」の基盤機能を実装・公開。

### Added
- パッケージのエントリポイントと公開APIを追加
  - src/kabusys/__init__.py: __version__ = "0.1.0", __all__ = ["data", "strategy", "execution", "monitoring"]。

- 環境変数・設定管理
  - src/kabusys/config.py:
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 解析で export 形式、クォート・エスケープ、インラインコメント等に対応するパーサ実装。
    - 既存 OS 環境変数を保護する protected パラメータの導入（.env 上書き制御）。
    - Settings クラスを提供し、J-Quants / kabuAPI / LINE / DB / 監視設定等の環境変数取得（バリデーション含む）。

- AI（NLP）関連
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols から銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を計算。
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
    - バッチ処理（最大 20 銘柄／コール）、記事数・文字数制限、レスポンス検証、±1.0 クリップ、部分成功時の DB 上書き戦略を実装。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ実装。
    - テスト用に _call_openai_api の差し替えが可能（unittest.mock.patch を想定）。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存。
    - マクロニュース抽出のためのキーワードリスト、LLM 呼び出し（gpt-4o-mini）、JSON 出力パース、リトライ・フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - DuckDB を用いた冪等な market_regime テーブルへの書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止のため、target_date 未満データのみを使用する設計。

- データプラットフォーム（DuckDB ベース）
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理ロジック（market_calendar テーブル）を実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを提供。
    - DB 未取得時の曜日ベースフォールバック、最大探索日数ガード、バックフィルや健全性チェックを実装。
    - calendar_update_job により J-Quants からの差分取得→保存フローを実装（バックフィル考慮）。

  - src/kabusys/data/pipeline.py / etl.py:
    - ETLResult（dataclass）を公開（src/kabusys/data/etl.py で再エクスポート）。
    - ETL の差分取得・保存・品質チェックのための基盤（差分計算、backfill、品質問題の集約、エラー情報の保持）を実装。
    - DuckDB のテーブル存在確認、最大日付取得等のユーティリティを実装。

- リサーチ（ファクター・特徴探索）
  - src/kabusys/research/factor_research.py:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR）、Value（PER, ROE）等のファクター計算関数を実装。
    - DuckDB 上の SQL ウィンドウ関数を活用した効率的な計算を採用。結果は (date, code) をキーにした dict リストで返却。
    - データ不足時の None 戻りなど堅牢性を考慮。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman の ρ に基づくランク相関）、ランク変換、ファクター統計要約（factor_summary）を実装。
    - pandas 等に依存しない純 Python 実装。ties の取り扱い（平均ランク）や小数丸め対策を実装。

- テスト・運用支援
  - 各種モジュールにおいて外部 API 呼び出しを差し替え可能にするフック（主に _call_openai_api）を用意し、単体テストを容易化。

### Changed
- （初版）設計方針ドキュメント的コメントを豊富に実装内に含め、各関数の前提・フォールバック・例外ポリシーを明示。

### Fixed
- N/A（初回リリースのためバグ修正履歴はなし。ただしコード中に多くのフォールトトレランス実装を含む: API 例外時のフォールバック、JSON パースの救済処理、DuckDB executemany の空リスト回避など）。

### Security
- 機密情報（OpenAI API キー等）を必須にするが、Settings 経由で環境変数管理を強調。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
- .env の過度な上書きを防ぐため OS 環境変数を protected として扱う設計。

### Known limitations / Notes
- OpenAI のレスポンスに依存する部分は外部 API の状況によりスコアが得られない場合がある。多くの箇所で失敗時に 0.0 を返す設計（フェイルセーフ）を採用しているため、API 連携障害時はスコアリングがスキップされるがシステムは致命的に停止しない。
- 日付・時間は明示的に UTC naive datetime / date を扱う箇所がある（news ウィンドウは UTC 変換ロジックを内部で扱う）。ルックアヘッドバイアスを避けるため、内部で datetime.today()/date.today() を参照しない実装方針を採用した箇所が存在する。
- DuckDB のバージョン差分（executemany の空リストやリストバインドの扱い）に配慮した実装を行っているが、実行環境の DuckDB バージョンに依存する可能性がある。
- 現時点で Strategy / Execution / Monitoring の具体的な発注ロジックや監視エンドポイントの実装は含まれておらず、データ基盤・リサーチ・AI スコアリング周りが中心。

---

作業ログや将来の変更（例: 0.2.0 の予定機能、セキュリティ改善、モデル切替時の互換性）については Unreleased セクションに記載していきます。必要であれば本 CHANGELOG を英語版に翻訳したり、各コミット・PR に紐付けた詳細な変更履歴に展開することも可能です。