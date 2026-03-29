# Changelog

すべての変更は Keep a Changelog のガイドラインに準拠しています。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-29

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能・設計方針は以下の通りです。

### Added
- パッケージ基盤
  - パッケージのバージョン設定と公開 API を追加（src/kabusys/__init__.py）。
  - サブモジュールのエクスポート: data, strategy, execution, monitoring。

- 設定管理
  - 環境変数 / .env 読み込みユーティリティを実装（src/kabusys/config.py）。
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env/.env.local を読み込む。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export KEY=... 形式やクォート・インラインコメント・エスケープを考慮した .env パーサを実装。
    - OS 環境変数を保護する protected オプションや override の挙動を提供。
    - Settings クラスでアプリケーション設定（J-Quants, kabu API, Slack, DB パス, 環境・ログレベル判定など）をプロパティとして公開。
    - KABUSYS_ENV / LOG_LEVEL の値検証を行い、不正な値で ValueError を送出する。

- AI（自然言語処理）関連
  - ニュース NLP スコアリング（銘柄ごとのセンチメント算出）を実装（src/kabusys/ai/news_nlp.py）。
    - target_date に対するニュースウィンドウを計算（前日 15:00 JST 〜 当日 08:30 JST の範囲を UTC に変換）。
    - raw_news と news_symbols を集約して銘柄ごとに最大記事数・最大文字数でトリム。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いてバッチ（最大 20 銘柄）でスコアリング。
    - 429・ネットワーク断・タイムアウト・5xx に対して指数的バックオフでリトライ、その他はフォールバックでスキップ。
    - レスポンスの厳密なバリデーションと ±1.0 でのクリップ。
    - DuckDB 向けの互換性対策（executemany に空リストを投げない等）。
    - unittest.mock.patch により OpenAI 呼び出しを差し替え可能な設計（テスト容易性を考慮）。

  - 市場レジーム判定モジュールを実装（src/kabusys/ai/regime_detector.py）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは OpenAI (gpt-4o-mini) を使用。APIの再試行とフェイルセーフ（失敗時は macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみ参照し、datetime.today()/date.today() を参照しない実装方針を採用。
    - 結果は DuckDB の market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。

- データ基盤（Data）
  - ETL パイプライン関連（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）。
    - ETL 実行結果を表す ETLResult データクラスを実装（取得数、保存数、品質問題、エラー一覧等を保持）。
    - 差分更新、バックフィル、品質チェックの方針をコードとドキュメントで反映。
    - ETLResult を外部に再エクスポート（src/kabusys/data/etl.py）。

  - カレンダー管理（src/kabusys/data/calendar_management.py）。
    - market_calendar テーブルを利用した営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合は曜日ベース（土日を非営業日）でのフォールバックを行う。
    - calendar_update_job を実装：J-Quants から差分取得して market_calendar を冪等更新（バックフィル、健全性チェックを含む）。
    - 最大探索日数やバックフィル、サニティチェック等の安全対策を実装。

- リサーチ（研究）モジュール
  - ファクター計算（src/kabusys/research/factor_research.py）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）や流動性指標を DuckDB の prices_daily / raw_financials から計算する関数群を実装。
    - データ不足時は None を返す等、頑健な実装。

  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）。
    - ランク変換・統計サマリー（factor_summary）等のユーティリティ。
    - 外部依存を避け、標準ライブラリのみで実装。

### Changed
- 設計上の重要な方針（プロジェクト開始時点のドキュメント的明記）
  - ルックアヘッドバイアス対策として、date/target_date を明示して日付参照を一貫して行う設計（datetime.today()/date.today() を直接利用しない）。
  - データベース書き込みは可能な限り冪等性を保つ（DELETE→INSERT、ON CONFLICT など）。
  - OpenAI 呼び出しはモジュール毎に独立したラッパー関数を持ち、テスト時の差し替えを容易にしている。

### Fixed
- DuckDB 互換性および堅牢性の考慮
  - DuckDB 0.10 の executemany に対する注意（空リストを送らない）を反映し、空の場合の分岐を追加。
  - DB 書き込み中の例外発生時に ROLLBACK を試み、Rollback 失敗時は警告ログ出力するフォールバック処理を追加。

### Security
- API キーの扱い
  - OpenAI API キーは引数から注入可能で、なければ環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に失敗させる。
  - .env 読み込みで OS 環境変数上書き保護（protected set）を実装し、意図しない上書きを防止。

### Notes / Implementation Details
- OpenAI モデル: gpt-4o-mini を前提にプロンプトと JSON Mode 指定で実装。
- ニュースウィンドウ（news_nlp）:
  - JST の前日 15:00 〜 当日 08:30 を UTC に変換して DB の raw_news（UTC 保存）と比較する。
  - 1 銘柄あたり最大記事数・最大文字数を設定してトークン肥大化を抑制。
- Market Regime 判定の重み付けと閾値:
  - 移動平均乖離の重み 0.7、マクロニュースの重み 0.3。スコアは ±1.0 でクリップ。
  - bull/bear 判定閾値は 0.2 に設定。
- テスト容易性:
  - OpenAI API 呼び出し箇所は内部関数（_call_openai_api）として分離しており、unit test で簡単にモック可能。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装と統合テストの追加。
- OpenAI 呼び出しの並列化やトークン利用最適化。
- より詳細な品質チェックルールと自動リカバリ機能の追加。

---

参照:
- 各モジュールの docstring に主要な設計方針・処理フローを記載しています。必要に応じて該当ソースを参照してください。