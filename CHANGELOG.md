# Changelog

すべての重大な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」仕様に準拠します。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- バージョニング: Semantic Versioning を想定

## [Unreleased]

- 今後のリリースに向けた未実装／改善候補の追記領域。

---

## [0.1.0] - 2026-03-27

初回リリース。日本株自動売買プラットフォームの初期実装を追加しました。主な機能・設計方針は以下の通りです。

### 追加 (Added)

- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = "0.1.0"）および公開モジュール指定（data, strategy, execution, monitoring）。
  - パッケージ全体で DuckDB を主要なローカル DB として使用。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能（プロジェクトルート判定は .git または pyproject.toml を使用）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサ実装:
    - export KEY=val 形式対応、
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、
    - インラインコメント処理（クォート外で '#' の直前がスペース/タブの場合にコメント扱い）、
    - 無効行のスキップ。
  - Settings クラスを公開（jquants_refresh_token、KABU/API、Slack、DBパス、環境種別、ログレベル等のプロパティ）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証（許容値チェック）を実装。
  - 必須環境変数未設定時には明示的な ValueError を送出。

- AI（LLM）モジュール (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントスコアを取得。
    - タイムウィンドウ: JST 前日15:00 ～ 当日08:30（UTC に変換して DB 比較）。
    - バッチ処理（1 API 呼び出しで最大 20 銘柄）。
    - 1銘柄あたり最大記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）によりトークン肥大化を抑制。
    - 再試行戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンス検証ロジック（JSON パース、"results" フォーマット、コード照合、スコア数値チェック、±1.0 クリップ）。
    - スコア取得後、部分失敗に耐性を持たせるため取得済みコードのみ DELETE→INSERT で置換して書き込み（DuckDB の executemany 空リスト制約回避も考慮）。
    - API キーは引数または OPENAI_API_KEY 環境変数から解決。未設定時は ValueError。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロキーワードによる raw_news フィルタリング、LLM（gpt-4o-mini）による宏観センチメント評価、スコア合成とクリッピング。
    - API 呼び出し失敗時は macro_sentiment=0.0 としてフェイルセーフに継続。
    - 計算結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。
    - API キーの解決方法は news_nlp と同様。未設定時は ValueError。

  - 両モジュール共通
    - OpenAI 呼び出しは内部ラッパー関数化しテスト時に差し替え可能（unittest.mock.patch を想定）。
    - LLM 呼び出しでのエラーやパース失敗はログを残して安全にフォールバックする設計（例外を投げないケースが多い）。

- リサーチ・ファクター類 (src/kabusys/research)
  - factor_research.py
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Value（PER、ROE）、Volatility（20日 ATR）、Liquidity（20日平均売買代金・出来高変化率）等の計算関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用し、data のスキャン範囲や不足データ時の None 処理を明示。
    - 結果は (date, code) をキーとする dict リストで返却。
  - feature_exploration.py
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）計算（Spearman の ρ の実装）、rank、factor_summary 等の統計ユーティリティを追加。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - パッケージ公開 API を __init__ で整理（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。

- データプラットフォーム（src/kabusys/data）
  - calendar_management.py
    - market_calendar テーブルを用いた営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB に値がない場合は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィル、健全性チェック（将来日付の異常検出）を実装。
  - pipeline.py / etl.py
    - ETL パイプラインの骨格を実装（差分取得、idempotent 保存、品質チェックフロー）。
    - ETLResult dataclass を公開（kabusys.data.etl で再エクスポート）。ETL 結果の集約、品質問題の収集、エラー有無判定、辞書化（監査ログ向け）。
    - 差分更新のための最小日付、カレンダー先読み、バックフィル日数等の定数を定義。
    - 品質チェックでの問題は収集するが、ETL は継続して全件チェック結果を返す（Fail-Fast ではない設計）。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティを実装。

- その他
  - jquants_client など外部クライアントはモジュール参照（データ取得 / 保存処理は jquants_client を想定）。
  - ロギングを随所に配置しデバッグ・運用観測を容易に。

### 変更 (Changed)

- 該当なし（初回リリース）。

### 修正 (Fixed)

- 該当なし（初回リリース）。

### セキュリティ (Security)

- 環境変数（API キー・Slack トークン・kabu パスワード等）は Settings 経由で必須チェックを行い、未設定時に早期にエラーを出すことで誤動作を防止。
- .env 自動ロード時に現行 OS 環境変数を保護する（.env.local は上書き可能だが OS 環境変数はデフォルトで保護）。

### 既知の制約・設計上の注意点

- ルックアヘッドバイアス防止のため、内部ロジックで datetime.today() / date.today() を直接参照しない設計方針を基本とするが、calendar_update_job は実運用の夜間バッチとして date.today() を使用する。
- OpenAI 連携は gpt-4o-mini と JSON Mode を前提に実装している（将来のモデル変更時はラッパーを調整）。
- DuckDB の executemany における空リストバインドの制約を考慮して空チェックを厳密に行っている。
- 部分失敗時のデータ保護（部分的な DELETE→INSERT）により、API 部分障害でも既存スコアを破壊しない実装を採用。

---

（参考）今後の項目候補
- strategy / execution / monitoring の具体実装（発注ロジック、リスク管理、Slack 通知等）
- 単体テスト・統合テストの追加と CI/CD パイプライン構成
- API クライアント（jquants, kabu）周りの抽象化とモック提供
- パフォーマンス改善（大規模銘柄数時のバッチ最適化）、メトリクス収集

--- 

注: 本 CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートとして使用する場合は、追加の運用上の変更点やマイグレーション手順等を追記してください。