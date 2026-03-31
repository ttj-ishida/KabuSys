# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-31

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。
主にデータ取得・ETL、カレンダー管理、研究用ファクター計算、ニュース NLP（OpenAI）を含むAIモジュール、環境設定周りのユーティリティを提供します。

### Added
- パッケージ初期化
  - src/kabusys/__init__.py にパッケージメタ情報（__version__ = "0.1.0"）と公開サブパッケージ定義を追加。

- 環境変数・設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
    - export KEY=val 形式やクォート内のエスケープ、インラインコメントの取り扱いに対応したパーサを実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / ログレベル / 環境種別 等の設定プロパティ（必須項目は未設定時に ValueError を発生）を定義。
    - 有効値検証（KABUSYS_ENV, LOG_LEVEL）を実装。

- ニュース NLP（AI）モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）に対してバッチでJSON出力を要求してセンチメント（-1.0〜1.0）を算出。
    - ウィンドウ算出（前日 15:00 JST ～ 当日 08:30 JST、UTC変換）を実装（calc_news_window）。
    - バッチサイズ、記事数・文字数上限、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスの厳密なバリデーション（JSON抽出・results配列チェック・コード照合・数値検査）を実装。
    - ai_scores テーブルへの冪等的な置換（DELETE → INSERT）を実装。部分失敗時に既存スコアを保護するため、書き込むコードを限定。
    - 公開 API: score_news(conn, target_date, api_key=None)

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（重み70%）と、news_nlp により得たマクロセンチメント（重み30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込む。
    - OpenAI 呼び出しは独立実装で、API失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフを採用。
    - 冪等的な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（Data）モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー（market_calendar）を扱う夜間バッチ更新ジョブ(calendar_update_job)と、営業日判定/探索ユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫したロジックを採用。
    - 最大探索日数制限やバックフィル、健全性チェックの実装。

  - src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
    - ETL パイプライン用ユーティリティと ETLResult データクラスを追加（取得数・保存数・品質チェック結果・エラー集約）。
    - 差分更新・バックフィル方針、品質チェックの扱い（重大度に応じたフラグ）などの設計に対応。

- Research（リサーチ）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M リターン, ma200乖離）、ボラティリティ（20 日 ATR, 相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装。
    - calc_momentum, calc_volatility, calc_value として公開。DuckDB を用いた SQL ベースの実装で、外部 API に依存しない。データ不足時は None を返す設計。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算(calc_forward_returns)、IC（Information Coefficient）計算(calc_ic)、ランク変換(rank)、カラム統計サマリ(factor_summary) を実装。
    - ランク相関は Spearman（ランクの Pearson）により算出。ties は平均ランクで処理。
    - pandas 等の外部ライブラリに依存せず標準ライブラリのみで実装。

- データユーティリティ
  - src/kabusys/data/calendar_management.py / pipeline.py 等で DuckDB を標準的なストレージとして使用（テーブル操作・範囲検索・window関数など多用）。
  - jquants_client 経由の保存/取得処理を参照する設計（実装は別モジュール想定）。

### Changed
- （初版のため該当なし）初期実装に集中。

### Fixed
- （初版のため該当なし）

### Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY をサポート。キー未設定時は ValueError を発生させることで誤用を防止。

### Notes / Implementation details（重要な設計判断）
- ルックアヘッドバイアス対策
  - news_nlp/regime_detector 等の全 AI/研究処理は内部で datetime.today()/date.today() を参照せず、明示的な target_date を受け取り target_date 未満/前日のデータのみを使用することで将来情報の混入を防止。
- フェイルセーフ
  - OpenAI 呼び出しや外部 API の一時失敗に対してはリトライやバックオフを実装し、最終的には無害なデフォルト値（例: macro_sentiment=0.0）で継続する設計。
- 冪等性
  - DB への書き込みは基本的に冪等性（DELETE→INSERT、ON CONFLICT 更新想定）を重視している。
- DuckDB バージョン互換
  - executemany に空リストが渡せない問題（DuckDB 0.10）を考慮したガードを実装。

### Breaking Changes
- （初版のため該当なし）

---

今後のリリースでは、以下を予定しています（例）:
- J-Quants / kabu API クライアントの統合テストと実運用での堅牢化
- ストラテジー実行/発注モジュールの実装
- モニタリング・アラート機能の拡充
- ドキュメント（Usage / API）の充実

ご要望や発見された問題は issue を作成してください。