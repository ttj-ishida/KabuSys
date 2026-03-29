# CHANGELOG

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-29
初回リリース。日本株のデータ取得・ETL・研究・AI ベースのニュース解析・市場レジーム判定を含む自動売買／リサーチ基盤のコア機能を提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として公開。
  - パッケージ公開用のトップレベルエクスポートを定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - プロジェクトルート判定は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
  - .env パーサーは export 構文、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント等に対応。
  - 必須環境変数未設定時は明確なエラーメッセージを投げる `_require` を提供。
  - 各種設定プロパティを持つ `Settings` クラスを公開（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等）。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP スコアリング (`news_nlp.score_news`)
    - 指定日を基準としたニュースウィンドウ（JST 前日15:00〜当日08:30）で記事を集約して銘柄ごとにセンチメントを算出。
    - OpenAI（gpt-4o-mini）の JSON Mode を用いたバッチ（最大 20 銘柄/コール）でのスコアリング。
    - トークン肥大対策（記事数上限、文字数トリム）を実装。
    - 429・ネットワーク・タイムアウト・5xx は指数バックオフでリトライ。部分失敗に配慮して DB 書き込みは取得済みコードのみ置換（DELETE→INSERT）。
    - レスポンス検証（JSON パース、results 配列、code/score 構造、数値チェック）を実装し、不正レスポンスはスキップ。
    - テスト用に内部の API 呼出しを差し替え可能（unittest.mock.patch で _call_openai_api をモック可）。
  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出して `market_regime` テーブルへ冪等書き込み。
    - マクロキーワードによる記事抽出、OpenAI を用いたマクロセンチメント評価、スコア合成、閾値によるラベル付けを実装。
    - API エラーやパース失敗時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT を行い、失敗時は ROLLBACK を試行して例外を伝播。

- データ & ETL (`kabusys.data`)
  - ETL パイプライン (`data.pipeline.ETLResult` を含む)
    - 差分更新、バックフィル、品質チェックを想定した ETLResult データクラスを提供。品質問題の収集・判定（重大度判定）を行えるよう設計。
    - DuckDB を前提とするユーティリティ（テーブル存在確認、最大日付取得など）を実装。
    - ETL は id_token 注入などテストしやすい設計。
  - ETL の公開インターフェース `data.etl` で ETLResult を再エクスポート。
  - マーケットカレンダー管理 (`data.calendar_management`)
    - JPX カレンダーの夜間差分更新ジョブ（J-Quants 経由）と `market_calendar` テーブルの冪等保存を実装（calendar_update_job）。
    - 営業日判定ユーティリティ群を提供: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。探索範囲制限（最大検索日数）や健全性チェック、バックフィルを備える。
  - J-Quants クライアント (`data.jquants_client`) を利用した保存処理の想定（fetch/save のラッパー呼び出しを使う設計）。

- 研究用モジュール (`kabusys.research`)
  - ファクター計算 (`research.factor_research`)
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算する `calc_momentum`。
    - Volatility / Liquidity: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、volume_ratio を計算する `calc_volatility`。
    - Value: 最新財務データから PER / ROE を計算する `calc_value`（raw_financials と prices_daily を参照）。
    - すべて DuckDB 上で SQL を駆使して計算し、結果を (date, code) ベースの辞書リストで返す。
  - 特徴量探索 (`research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、デフォルト [1,5,21]）。
    - IC（Spearman の rho）計算 `calc_ic`、ランク化ユーティリティ `rank`。
    - ファクター統計サマリー `factor_summary`。
  - 研究 API は外部注文や本番口座に一切アクセスしない設計（安全性）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 注意事項 / 設計上のポイント
- ルックアヘッドバイアス対策:
  - AI / 研究モジュールは内部で datetime.today()/date.today() を直接参照しない設計（呼び出し側が target_date を渡す）。
  - データ取得 SQL は target_date より前のデータのみを参照する等の配慮あり。
- フェイルセーフ動作:
  - OpenAI API の失敗やレスポンスパース失敗は基本的に致命的エラーとせずフォールバック（0.0）やスキップで継続するよう設計。
- DB 書き込みの冪等性と部分失敗保護:
  - AI スコアやレジームの書き込みは、既存行の削除→挿入のパターンで冪等に保存。部分失敗時には他コードの既存スコアを保護する実装。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部で関数化しており、ユニットテスト時に差し替え可能。
- 依存:
  - DuckDB を主要な永続化層として利用。
  - OpenAI の SDK（chat/completions）を利用して LLM と通信。
  - J-Quants クライアントを通じたマーケットデータ取得を想定。

---

今後のリリースでは、strategy / execution / monitoring に関連する発注ロジック・実運用連携・監視・通知機能の追加や、より詳細な品質チェック・メトリクス出力を予定しています。