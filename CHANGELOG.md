# Changelog

すべての注目すべき変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初回リリース。日本株自動売買・データ基盤向けのコアモジュール群を実装しました。主要な機能は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理 (`kabusys.config`)
  - .env/.env.local ファイルおよび環境変数からの設定読み込みを自動で行う機能を実装。
    - プロジェクトルートは .git / pyproject.toml を探索して特定（CWD 非依存）。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - .env パーサ実装:
    - コメント・export プレフィックス対応。
    - シングル/ダブルクォートのバックスラッシュエスケープ処理対応。
    - 非クォート値におけるインラインコメント処理（直前が空白/タブの場合のみ）。
  - override/protected オプションを用いた安全な環境変数上書きロジック。
  - Settings クラスを提供（型変換・デフォルト・バリデーション含む）。
    - J-Quants / kabuステーション / Slack / DB / 監視 / システム設定をプロパティで取得。
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック。
    - パス類は pathlib.Path で返却、しきい値は float として返却。

- データプラットフォーム (`kabusys.data`)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - DB データ優先、未取得日は曜日ベースでフォールバックする一貫した判定ロジック。
    - calendar_update_job により J-Quants からの差分取得と冪等保存を実装（バックフィル対応、健全性チェック）。
  - pipeline / etl:
    - ETLResult データクラスを実装して ETL 実行結果をまとめて返却・ログ化可能に。
    - 差分取得・バックフィル・品質チェックを想定した設計（jquants_client / quality 連携想定）。
  - etl モジュールから ETLResult を再エクスポート。

- AI / 自然言語処理 (`kabusys.ai`)
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄別にニュースを結合して OpenAI（gpt-4o-mini, JSON Mode）へバッチで投げ、センチメント（ai_score）を ai_scores テーブルへ保存する処理を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）を行う calc_news_window。
    - バッチサイズ、文字数・記事数制限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ・再試行を実装。
    - レスポンスの厳格なバリデーション（JSON 解析、results 配列、code/score の検証、数値クリップ）と、部分失敗時に他銘柄スコアを保護する DB 書き込み戦略（DELETE → INSERT）を採用。
    - ルックアヘッドバイアス防止のため datetime.today() を直接参照しない設計。
  - regime_detector:
    - ETF 1321（日経225 連動）200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を用いたスコア計算、OpenAI 呼び出し（gpt-4o-mini）・再試行、フェイルセーフ（API 失敗時は macro_sentiment=0.0）、および market_regime テーブルへの冪等書き込みを実装。
    - LLM 呼び出しはモジュール内プライベート関数で独立実装（モジュール結合を避ける）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - factor_research:
    - モメンタム (1M/3M/6M リターン、200 日 MA 乖離)、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金・出来高比率）、バリュー（PER, ROE）を DuckDB 上の SQL と Python で計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - データ不足時に None を返す等の頑健な設計。
  - feature_exploration:
    - 将来リターン算出 calc_forward_returns（任意ホライズン対応）、IC（スピアマンランク相関）計算 calc_ic、ランク変換ユーティリティ rank、統計サマリー factor_summary を実装。
    - pandas 等の外部依存を避け、標準ライブラリと DuckDB のみで実装。
  - research.__init__ で主要関数を再エクスポート。

### 変更 (Changed)
- （初版のため過去リリースからの変更はなし。）
- 設計上の重要な方針が各モジュールに注記されている（例: ルックアヘッドバイアス防止、DB の冪等保存、API 呼び出しのフェイルセーフ/リトライ戦略）。

### 修正 (Fixed)
- （初版のため過去リリースからの修正履歴はなし）
- 実装上の耐障害性（OpenAI API の 5xx/タイムアウト/429 に対するリトライ、JSON パース失敗時のフォールバック、DB トランザクション時の ROLLBACK ハンドリングなど）に配慮したコードを実装。

### セキュリティ / 安全性 (Security / Safety)
- 環境変数読み込みで OS 環境変数を意図せず上書きしないよう protected 機構を導入。
- OpenAI API キーは explicit に引数から注入可能（テスト容易性と漏洩リスク低減）。
- DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のトランザクショナルな処理とし、例外時は ROLLBACK を試行。

### 既知の制約・注意点 (Known limitations / Notes)
- OpenAI 呼び出しは gpt-4o-mini の JSON mode を想定しているため、API 仕様変更時は影響を受ける可能性あり。
- DuckDB バインド挙動（executemany に空リスト不可など）への互換性考慮があり、そのためのガードを実装している。
- calendar_update_job・ETL パイプラインは jquants_client / quality 等の外部モジュールとの連携を前提としており、実行環境で該当クライアントが必要。

---

今後の予定（例）
- strategy / execution / monitoring モジュールの実装・ドキュメント強化
- 単体テストの追加（特に OpenAI 呼び出しまわりはモック化しての網羅）
- CI 上での品質チェック自動化（lint, type check, duckdb compatibility）

（本 CHANGELOG はソースコードの内容から機能・設計方針を推測して作成しています。実際のリリースノートや公開日等はリポジトリの管理者の記録を参照してください。）