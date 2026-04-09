# Changelog

すべての注目すべき変更点を時系列で記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買システムのコアライブラリを実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。__version__ = 0.1.0。
  - 公開モジュール群のエントリポイントを定義（data, strategy, execution, monitoring を想定したパッケージ構成）。
- 環境設定（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git / pyproject.toml ベース）。
  - .env パーサを実装（export プレフィックス対応、クォート中のエスケープ処理、インラインコメント処理）。
  - 環境変数上書きポリシー（OS 環境変数保護）とエラーハンドリング（読み込み失敗時の警告）。
  - Settings クラスを実装し、J-Quants / kabuステーション / LINE / DB パス / Paper Trading の挙動 /
    監視しきい値 / 環境（development, paper_trading, live）/ ログレベル等のプロパティを提供。
  - PAPER_FILL_MODE の検証やパスの Path 正規化等のユーティリティを追加。
- AI ニュース解析（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約して銘柄別にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードで
    センチメントスコアを取得するバッチ処理を実装。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST の UTC 変換）を提供（calc_news_window）。
  - バッチサイズ・記事・文字数トリム制御、指数バックオフのリトライ、レスポンスバリデーション、スコアの ±1.0 クリップ。
  - DuckDB へ冪等的に書き込むロジック（DELETE → INSERT。部分失敗時に既存スコアを保護）。
  - API キー注入（引数 or 環境変数 OPENAI_API_KEY）によるテスト容易性。
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して
    日次レジーム（bull / neutral / bear）を算出し market_regime テーブルへ書き込む処理を実装。
  - DuckDB からのデータ取得、マクロキーワード検索、OpenAI 呼び出し（リトライ・フォールバック）を含む一連のフローを実装。
  - ルックアヘッドバイアス防止設計（target_date 未満データのみを使用）や、API 失敗時のフェイルセーフ（macro_sentiment=0.0）。
- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定（is_trading_day）、SQ 判定、前後の営業日探索（next_trading_day / prev_trading_day）、
      期間内営業日取得（get_trading_days）を実装。
    - DB 未取得時の曜日ベースのフォールバック、最大探索範囲ガード、DuckDB 型変換ユーティリティを実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants クライアント経由で差分取得 → 保存（保存は jquants_client へ委譲）。
  - ETL / パイプライン（pipeline）
    - ETLResult データクラスを公開。ETL 実行の取得数・保存数・品質問題・エラー集約のための構造を提供。
    - ETL の設計方針に基づく差分取得／バックフィル／品質チェックを想定したインターフェースを整備（jquants_client, quality モジュールを利用）。
  - etl モジュールで ETLResult を再エクスポート。
- 研究用ユーティリティ（kabusys.research）
  - factor_research モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - モメンタム（1/3/6M、ma200乖離）、ATR ベースのボラティリティ、流動性指標、raw_financials からの PER/ROE 取得等を提供。
    - DuckDB を用いた SQL 実装で、過不足データに対する None ハンドリングを実装。
  - feature_exploration モジュールを実装（calc_forward_returns, calc_ic, factor_summary, rank）。
    - 将来リターンの一括取得（任意ホライズン）、Spearman（ランク相関）による IC 計算、ファクター統計サマリーを提供。
    - pandas 等に依存しない標準ライブラリベースの実装。
- テスト・運用を意識した設計上の配慮
  - OpenAI 呼び出し部はモジュール内でラップし、テスト時に差し替え可能（unittest.mock.patch を想定）。
  - DuckDB との互換性・実行時制約（executemany の空リスト回避等）に配慮した実装。
  - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で行い、失敗時は ROLLBACK を行うよう設計。
  - ルックアヘッドバイアス回避のため、内部で datetime.today()/date.today() を直接参照しない設計（target_date を明示的に受け取る）。

### Fixed
- 初期リリースにつき既知のバグ修正履歴はなし。実装時に堅牢性（例外処理、ログ出力、リトライ/バックオフ、フェイルセーフ）を考慮。

### Breaking Changes
- なし（初回リリース）。

### Security
- OpenAI API キーは引数で注入可能かつ環境変数 OPENAI_API_KEY を使用。.env 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。

注記:
- 各モジュールは外部 API（J-Quants / OpenAI 等）や DuckDB スキーマに依存します。データベース側のテーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar など）が想定通り存在することを前提としています。