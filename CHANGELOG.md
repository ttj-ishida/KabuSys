# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初版の公開。
- 基本パッケージ情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py に定義）
  - パブリック API のエクスポート: data, strategy, execution, monitoring

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - .env/.env.local の読み込み順序、OS 環境変数の保護（protected set）をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供（テスト向け）。
  - export KEY=val 形式やクォート内のエスケープ、行末コメントの取り扱い等をサポートする堅牢な .env パーサーを実装。
  - 必須パラメータ取得ヘルパー _require と Settings クラスを提供。J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証などのプロパティを公開。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live / is_paper / is_dev の便利プロパティ。

- AI 関連機能 (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）に JSON Mode でバッチ送信して銘柄ごとのセンチメント ai_score を生成、ai_scores テーブルへ冪等的に書き込む。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を calc_news_window として提供。
    - バッチサイズ、記事／文字数のトリム、レスポンス検証、スコアの ±1.0 クリップ、再試行（429/ネットワーク/5xx の指数バックオフ）に対応。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（_call_openai_api を unittest.mock.patch で差し替えられる）。
  - レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込み。
    - マクロ記事検索（マクロキーワード一覧）、OpenAI 呼び出しの再試行・フォールバック（失敗時 macro_sentiment = 0.0）、JSON レスポンス処理を実装。
    - lookahead バイアス防止設計（date 判定は引数の target_date ベースで行い、DB クエリは target_date 未満で限定）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを利用した営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータがない場合の曜日ベースのフォールバック、最大探索日数による安全策、JPX カレンダー差分取得ジョブ calendar_update_job（J-Quants クライアント連携・バックフィル・健全性チェック）を実装。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - 差分取得・保存・品質チェックを行う ETL 設計。ETLResult データクラスを実装し公開（etl.py で再エクスポート）。
    - ETLResult に品質問題・エラーの集約、has_errors / has_quality_errors 判定、辞書変換 to_dict を実装。
    - DuckDB を用いたテーブル存在チェック、最大日付取得、トレーディング日補正などのユーティリティ関数を提供。

- Research モジュール (src/kabusys/research)
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily / raw_financials から計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時は None を返すなど安全な挙動。
    - 結果は (date, code) を含む dict のリストで返却。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman ランク相関）、ランク付けユーティリティ、統計サマリー（factor_summary）を実装。
    - 外部依存を持たず標準ライブラリで完結。欠損・非有限値の除外、ホライズンバリデーション等を実装。

- 共通実装
  - DuckDB を主要な解析・永続化のバックエンドとして使用。
  - データベース書き込みは冪等性を意識（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK）して実装。
  - 多くの箇所で lookahead バイアス防止を意識し、datetime.today()/date.today() を直接参照しない設計を採用（target_date を引数として受ける）。

### Changed
- 初版につき履歴なし（初期実装）。

### Fixed
- 初版につき履歴なし（初期実装）。

### Security
- 環境変数の自動ロードで OS 環境変数を保護する仕組み（protected set）を実装。
- OpenAI API キーはパラメータ注入または環境変数でのみ扱い、未設定時は明示的に ValueError を発生させることで誤動作を防止。

### Notes / Known limitations
- OpenAI との通信は gpt-4o-mini を想定しており、環境に応じた API キーの設定が必要。
- DuckDB のバージョン差異（例: executemany に空リストを渡せない点）に配慮した実装が行われているが、実運用環境での細かい互換性確認を推奨。
- news_nlp / regime_detector ともに LLM の出力に依存するため、レスポンス形式に不整合があった場合はログ記録のうえフェイルセーフによりスキップまたは中立値で継続する設計。
- 本リリースでは PBR・配当利回り等一部バリューファクターは未実装。

## 参考
- ソース内に詳細な設計ノート（lookahead バイアス対策、リトライ方針、冪等書き込み、テストフック等）が記載されています。実装の詳細や運用方針は各モジュールの docstring を参照してください。