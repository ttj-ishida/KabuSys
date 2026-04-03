# CHANGELOG

すべての注目すべき変更はここに記録します。  
このプロジェクトは Keep a Changelog の形式に準拠しています。

## [Unreleased]

---

## [0.1.0] - 2026-04-03

初回公開リリース。

### 追加 (Added)
- パッケージの基本構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - プロジェクトルートは __file__ を基準に .git または pyproject.toml を探索して判定（CWD に依存しない）。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供（settings インスタンスをエクスポート）。
    - J-Quants / kabuAPI / LINE / DB パス / 監視閾値 / ログ設定等のプロパティを定義。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装。
    - 必須キー未設定時は ValueError を送出する _require ヘルパー。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。
    - バッチ処理（最大 20 銘柄/チャンク）、記事トリム（記事数・文字数制限）、リトライ（429/ネットワーク/5xx に対する指数バックオフ）を実装。
    - レスポンスのバリデーションと ±1.0 のクリッピングを実施。
    - 成功した銘柄のみ ai_scores テーブルの当日データを置換（DELETE → INSERT）して部分失敗時の保護を実現。
    - タイムウィンドウ計算 (前日 15:00 JST ～ 当日 08:30 JST) を calc_news_window として提供。
  - regime_detector.score_regime
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - LLM 呼び出しは専用実装（news_nlp とプライベート関数を共有せずモジュール結合を低減）。
    - API エラー時は macro_sentiment=0.0 にフォールバック、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - lookahead バイアス対策として target_date 未満のデータのみを参照する設計。

- データ（Data Platform）モジュール (kabusys.data)
  - calendar_management
    - JPX カレンダー管理機能（market_calendar テーブル操作、営業日判定、next/prev/get_trading_days、is_sq_day）。
    - DB 登録がない場合は曜日ベース（土日除外）でフォールバックする一貫したロジック。
    - 夜間バッチ job: calendar_update_job を実装（J-Quants API から差分取得・バックフィル・健全性チェック）。
    - 最大探索範囲制限やバックフィル等の安全策を導入。
  - pipeline / etl
    - ETLResult データクラス公開（kabusys.data.etl 経由で再エクスポート）。
    - pipeline モジュールに基づく ETL 設計（差分取得、idempotent 保存、品質チェックのフロー設計）。
    - ETLResult は品質問題・エラーサマリを保持し、辞書化 API を用意。

- リサーチ（研究）モジュール (kabusys.research)
  - factor_research
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）などのファクター計算関数を実装。
    - DuckDB に対する SQL を中心とした実装で、外部 API には依存しない。
    - 関数: calc_momentum, calc_volatility, calc_value。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を提供。
    - pandas 等に依存せず、純 Python + SQL（DuckDB）で実装。
  - research パッケージは主要 API を __all__ で公開。

- 共通実装・設計方針（全体）
  - DuckDB を主要データストアとして利用。多くの処理が DuckDB 接続を受け取る設計。
  - ルックアヘッドバイアス防止のため date.today()/datetime.today() を直接参照しない箇所が多く、target_date を明示的に受け取る設計を適用。
  - API 呼び出しに対してフェイルセーフ（失敗時はスキップ/デフォルト値）やリトライを採用し、ETL/スコアリング処理の堅牢性を高める。
  - DB 書き込みは冪等性を考慮（DELETE→INSERT、ON CONFLICT 想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）を使用。

### 変更 (Changed)
- なし（初回リリースのため差分なし）

### 修正 (Fixed)
- なし（初回リリース）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供する必要がある旨を明示。未設定時は ValueError を送出する箇所あり（score_news / score_regime）。
- 環境変数の自動ロードを無効化するオプション（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

---

注:
- 本 CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する場合は、テスト結果・既知の制限事項・マイグレーション手順などを追記してください。