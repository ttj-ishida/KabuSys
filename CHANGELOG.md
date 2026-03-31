# CHANGELOG

すべての重要な変更を記録します。これは Keep a Changelog の形式に準拠しています。  
フォーマットは将来のリリースや差分追跡を想定しています。

なお、本 CHANGELOG は現行コードベースの実装内容から推測して作成しています（ドキュメント的要約）。実装上の細かな差異は実コードを参照してください。

## [Unreleased]
（次回リリースに向けた保留事項や既知の改善点をここに記載してください）

- なし（初回公開相当のスナップショット）

## [0.1.0] - 2026-03-31

初回リリース。本リリースでは日本株自動売買システムのコアとなる以下の機能群を実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）、モジュール公開一覧を定義。
  - バージョン番号を "0.1.0" として設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - Settings クラスを導入し、環境変数経由でアプリ設定を取得する安全なインターフェースを提供。
  - J-Quants、kabuステーション、Slack、データベースパスなど主要な設定プロパティを実装（必須値判定は ValueError を送出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD フラグにより自動 .env 読み込みを無効化可能。
  - プロジェクトルートを .git または pyproject.toml で探索し、CWD に依存しない .env 自動読み込みを実装。
  - .env ファイルパーサ実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントルールに対応）。
  - .env と .env.local の読み込み優先度（OS 環境変数 > .env.local > .env）と保護（既存 OS 環境変数を protected として上書き防止）を実装。

- AI モジュール（src/kabusys/ai）
  - ニュースセンチメントスコアリング（news_nlp.py）
    - raw_news / news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON mode を用いて銘柄ごとのスコアを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大20銘柄/チャンク）・トークン肥大化対策（記事数・文字数上限）を実装。
    - 再試行（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで行う。致命的でない失敗はログを出してスキップ（フェイルセーフ）。
    - レスポンスの厳密なバリデーションと数値クリップ（±1.0）を実装。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - ニュース収集ウィンドウ計算（JSTベース → UTC naive datetime で扱う calc_news_window）を実装。
    - ルックアヘッドバイアス回避のため、内部で date.today()/datetime.today() を直接参照しない設計。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321（TOPIX連動等）200日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily からの MA 計算、raw_news からマクロキーワードで抽出したタイトルを LLM で評価、スコア合成後に market_regime テーブルへ冪等書き込みを行う。
    - OpenAI 呼び出しは独立実装で、API のエラー種別ごとにリトライ戦略を用意（再試行上限・バックオフ）。
    - マクロキーワードのリストやしきい値、モデル名（gpt-4o-mini）などを定数化。
    - API 失敗やパース失敗時は macro_sentiment=0.0 として処理継続（フェイルセーフ）。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを利用した営業日判定 API を提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日のフォールバックは曜日判定（土日除外）で一貫性を確保。
    - _MAX_SEARCH_DAYS による探索上限や健全性チェック、バックフィル戦略、JPX（J-Quants 経由）からの差分取得ジョブ（calendar_update_job）を実装。
    - jquants_client 経由のフェッチ／保存フックを想定（エラー時は安全にログ出力して 0 を返す）。

  - ETL パイプライン（pipeline.py, etl.py）
    - ETLResult データクラスを導入し、ETL 実行結果／品質問題／エラーを集約して返却する仕組みを実装。
    - 差分取得、バックフィル、品質チェックフローを想定したヘルパー（テーブル最終日取得など）を実装。
    - etl.py から ETLResult を再エクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（20日 ATR、相対 ATR、出来高系指標）、Value（PER、ROE）等のファクター計算を実装。
    - DuckDB SQL を用いた計算（prices_daily / raw_financials 参照）、データ不足時の None 返却などの堅牢なロジックを採用。
  - 特徴量探索・統計（feature_exploration.py）
    - 将来リターン計算（複数ホライズン）、IC（スピアマンランク相関）計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク付けユーティリティを実装。
    - pandas 等の外部依存を避け、標準ライブラリ＋DuckDBで実装。
  - research パッケージの public API を __init__ で整理（関数をエクスポート）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- API キーの取り扱いに関する注意点を実装レベルで配慮
  - OpenAI API キーは関数引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY からの解決をサポート。
  - 設定読み込みは .env を自動で読み込むが、KABUSYS_DISABLE_AUTO_ENV_LOAD によって CI/テストでの制御が可能。

### Notes / Implementation decisions
- ルックアヘッドバイアス回避:
  - AI スコアリングやリサーチ関数で date.today()/datetime.today() を直接参照しない設計。すべて target_date を明示的に受け取る。
- DB 書き込み:
  - AI スコアやレジーム書き込みは冪等性を考慮（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
  - DuckDB の executemany の挙動（空リスト不可）に配慮した実装。
- OpenAI 呼び出し:
  - gpt-4o-mini を利用、JSON mode（response_format={"type":"json_object"}）を採用。レスポンスパース失敗や API エラーに対する明確なフォールバックとログ出力を実装。
  - リトライ戦略（429/ネットワーク/タイムアウト/5xx に対する指数バックオフ）を実装。
- J-Quants / kabu API / Slack 等の外部クライアントはモジュール境界で抽象化し、呼び出し側では直接 API 実装に依存しない設計。
- テストフレンドリー:
  - _call_openai_api の差し替えや Settings の自動 .env ロード抑止フラグによりユニットテストがしやすい設計。

---

メジャーリリース規則: Semantic Versioning を想定しています。バグ修正は patch、後方互換の機能追加は minor、大きな互換性破壊は major として扱ってください。

（この CHANGELOG はコードベースから推測して作成しているため、ドキュメント目的での参考情報としてご利用ください。実際のリリースノート作成時はコミットログやリリース差分の確認を推奨します。）