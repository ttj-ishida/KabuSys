# CHANGELOG

すべての重要な変更点はここに記録します。本ファイルは「Keep a Changelog」記法に準拠します。

## [Unreleased]

- 今後のリリースに向けたメモや未確定の変更点を記載します。

---

## [0.1.0] - 2026-04-03

初回公開リリース。以下の主要機能・設計上の方針・実装詳細を含みます。

### 追加 (Added)
- パッケージ基本
  - kabusys パッケージの初期公開。バージョンは `0.1.0`。
  - パッケージ公開時に利用する公開モジュール群を `__all__` で定義（data, strategy, execution, monitoring）。

- 環境設定 / 設定管理
  - `kabusys.config.Settings` による環境変数ベースの設定取得を実装。
  - `.env` / `.env.local` の自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用に利用可能）。
  - `.env` パーサ実装（エクスポート形式 `export KEY=val`、クォート付き値のエスケープ、コメント処理などに対応）。
  - OS 環境変数保護（読み込み時に既存の OS 環境変数を上書きしない既定挙動、.env.local は override）。
  - 各種設定プロパティを提供（J-Quants、kabuステーション、LINE、データベースパス、監視閾値、ログレベル、実行環境判定など）。
  - 設定値のバリデーション（KABUSYS_ENV、LOG_LEVEL の有効値チェック、必須キー取得時のエラー通知）。

- データ (Data)
  - calendar_management:
    - JPX マーケットカレンダー管理（market_calendar テーブルの読み書き、営業日判定、next/prev/get_trading_days、SQ 判定）。
    - 夜間更新バッチ (`calendar_update_job`) を実装。J-Quants クライアント経由で差分取得し idempotent に保存。
    - DB にカレンダーが無い場合の曜日ベースフォールバック（週末除外）を提供。
    - 最大探索日数・バックフィル・健全性チェックの導入（無限ループ防止、極端な将来日付の検出）。
  - pipeline / etl:
    - ETL 用のデータクラス `ETLResult` を定義（取得数・保存数・品質問題・エラー集約・判定プロパティ）。
    - 差分取得・バックフィルの方針を実装（最終取得日の数日前から再取得）。
    - DuckDB 前提のテーブル存在チェックなどユーティリティを実装。
    - ETL 実行時の品質検査結果を収集する設計（品質エラーは収集して呼び出し元が判断）。
  - ETL/パイプライン用の互換性考慮（DuckDB の executemany と空リストの制約に対処）。

- 研究 (Research)
  - factor_research:
    - モメンタム（約1/3/6ヶ月のリターン、200日MA乖離）、ボラティリティ（20日ATR 等）、バリュー（PER、ROE）など複数ファクターを計算する関数を実装（DuckDB SQL ベース）。
    - データ不足時は None を返すなどロバストな挙動。
  - feature_exploration:
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリーを実装。
    - 外部依存を避け、標準ライブラリのみで統計処理を実装。
  - `kabusys.research.__init__` から主要関数を再エクスポート（研究用途の公開 API を整理）。

- AI モジュール
  - news_nlp:
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメント（ai_score）を算出、`ai_scores` テーブルへ置換的に書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティを提供（UTC naive datetime で DB と比較）。
    - バッチサイズ、1銘柄当たり最大記事数・文字数のトリム等でトークン肥大化を抑制。
    - レスポンスバリデーション（JSON の抽出、results 配列、コード一致、数値チェック、スコアクリップ）。
    - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフの実装。
    - テスト容易性のために OpenAI 呼び出し関数を差し替え可能（ユニットテスト用に patch できる設計）。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し、`market_regime` テーブルへ冪等書き込みする処理を実装。
    - マクロニュース抽出のためのキーワードリストを実装（日本・米国／グローバル系）。
    - OpenAI（gpt-4o-mini、JSON mode）呼び出し、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）、レスポンスパース失敗時のフォールバックを実装。
    - ルックアヘッドバイアス防止設計（target_date 未満のデータのみ参照、datetime.today() を参照しない等）。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の順で冪等性を保持。失敗時は ROLLBACK を試行し、失敗ログを記録。

- ロギング・監視・運用
  - 各モジュールで適切なログレベル・警告メッセージを追加（データ不足、API エラー、パース失敗、ROLLBACK失敗等）。
  - 設定で CPU/メモリ/ディスク閾値や PID/KILL フラグファイルパスなど監視設定を提供。

- 互換性 / テスト補助
  - OpenAI 呼び出し処理はモジュールごとに独立（プライベート関数を共有しない）に実装し、各テストで差し替え可能。
  - DuckDB の挙動（executemany の空リスト禁止）に対応するためのガード実装。

### 変更 (Changed)
- 設計方針として「ルックアヘッドバイアス防止」を全 AI・研究モジュールで徹底（内部で date.today()/datetime.today() を参照しない、target_date を明示的に受け取る設計）。
- DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT 相当の扱い）設計。

### 修正 (Fixed)
- .env のクォート付き値のエスケープ処理や、コメント取り扱いに関する細かな取りこぼしを考慮したパーサ実装により、実運用での .env 読み込みの堅牢性を向上。

### 注意事項 (Notes)
- OpenAI API キーは引数で注入可能。未指定の場合は環境変数 `OPENAI_API_KEY` を参照。未設定の場合は ValueError を送出するため、実行前の環境変数準備が必要です。
- news_nlp / regime_detector は gpt-4o-mini を前提にプロンプトと JSON mode を使用しているため、OpenAI SDK のバージョンや JSON Mode の挙動変化に注意してください。
- DuckDB 環境での互換性を前提とした実装（型と executemany の扱い）になっているため、異なる DB や古い DuckDB バージョンでは注意が必要です。
- `.env.local` を使うと OS 環境変数の上書きが可能（ただし protected による保護あり）。CI/テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して自動読み込みを無効化できます。
- calendar_update_job は J-Quants クライアント（jquants_client）を利用するため、API レスポンスや接続エラー時は安全に 0 を返して処理継続する設計です。

---

今後のリリースでは以下を予定しています（例）:
- strategy / execution / monitoring の具体的な実行ロジックとテストケースの追加
- J-Quants クライアントの実装詳細と認証フローの明確化
- CI 内でのインテグレーションテストおよびモックを用いたテストカバレッジ拡充

（必要であれば各機能ごとにより詳細な変更履歴を分割して記載します。）
