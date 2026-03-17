# Changelog

すべての注目すべき変更をここに記録します。本ファイルは "Keep a Changelog" の書式に準拠し、セマンティックバージョニングを採用します。

既往のリリース:
- 0.1.0 — 初期公開リリース（機能の骨格と主要コンポーネントを実装）

## [Unreleased]
（未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-17
初期リリース。日本株向け自動売買基盤のコア機能を実装しました。以下はコードベースから推測してまとめた主要な追加点・設計方針です。

### Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加（__version__ = 0.1.0）。
  - サブパッケージのエクスポート定義（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により、ワーキングディレクトリに依存しない自動 .env ロードを実現。
  - .env / .env.local の読み込み順序と override 動作、OS 環境変数保護（protected set）の仕組みを実装。
  - .env のパースロジックを強化（export 句、クォート・エスケープ、行末コメント処理などに対応）。
  - 必須設定の取得メソッド（_require）と環境値検証（KABUSYS_ENV, LOG_LEVEL の妥当性チェック）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。

- J-Quants クライアント（kabusys.data.jquants_client）
  - J-Quants API から日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダーを取得するクライアントを実装。
  - API レート制御（固定間隔スロットリング）を実装して 120 req/min を順守。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx で再試行。
  - 401 Unauthorized を受けた場合の自動トークンリフレッシュを1回のみ行い再試行する仕組み。
  - ページネーション対応（pagination_key を利用）で全件取得。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止する設計。
  - DuckDB への保存は冪等性を保つため ON CONFLICT DO UPDATE を使用（raw_prices, raw_financials, market_calendar）。
  - 数値変換ユーティリティ（_to_float, _to_int）を実装し、空値や不整合値に対して安全に対応。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news テーブルへ保存する仕組みを実装。
  - 記事IDは正規化した URL の SHA-256（先頭32文字）で生成し重複を排除。
  - URL 正規化でトラッキングパラメータ（utm_ など）除去、スキーム・ホスト小文字化、フラグメント除去、クエリソートを実施。
  - SSRF 対策:
    - fetch 前にホストがプライベートアドレスかを検査。
    - リダイレクト時にスキーム/プライベートアドレスを検査するカスタム RedirectHandler を導入。
    - 許可しないスキーム（file:, javascript:, mailto: 等）を拒否。
  - レスポンスサイズ制限（デフォルト 10 MB）および gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃に耐性を付与。
  - raw_news への保存はチャンク化して一括 INSERT、ON CONFLICT DO NOTHING と INSERT ... RETURNING により実際に挿入された ID を返す実装。
  - 記事→銘柄紐付け（news_symbols）機能を実装。銘柄抽出は本文＋タイトルから 4 桁コード（正規表現）で抽出し、既知銘柄セットに基づきフィルタ。
  - 複数記事分の銘柄紐付けは重複排除後にチャンク一括挿入を行う内部関数を提供。

- DuckDB スキーマ（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の各レイヤに対応するテーブル定義を作成。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリ向けのインデックスを複数定義（例: code×date, signal/status など）。
  - init_schema(db_path) により親ディレクトリ作成・DDL 実行を行い、冪等に初期化する API を提供。
  - get_connection(db_path) で既存 DB への接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ベースの ETL を想定したヘルパーを実装（最終取得日の検出、バックフィル日数による再取得）。
  - run_prices_etl などのジョブ用ユーティリティを実装（取得→保存→ログ出力の流れ）。
  - ETL 結果を表す ETLResult データクラスを提供し、品質チェック結果・エラーメッセージを集約できる設計。
  - 市場カレンダーの先読み（lookahead）や最小データ開始日の定義を含む設計方針を反映。
  - 品質チェック（quality モジュール）と連携する想定のインターフェースを用意（重大度分類対応）。

### Security / Reliability
- セキュリティ対策
  - RSS パーサに defusedxml を採用し XML 攻撃を軽減。
  - RSS フェッチ時の SSRF 対策（ホスト検査とリダイレクト検査）。
  - .env パースで不正な入力に対する堅牢な処理（クォート・エスケープ、コメント処理）。
- 信頼性対策
  - ネットワークエラーと HTTP ステータスに対する再試行ロジック（指数バックオフ、429 の Retry-After 優先）。
  - API レート制御（固定インターバル）によりレートリミット順守。
  - DB 操作はトランザクションで保護し、失敗時はロールバックして例外を再送出。
  - データ保存は冪等（ON CONFLICT 句）を基本とし、重複や再実行に耐える設計。

### Internal / Developer experience
- テストしやすさを考慮した設計
  - RSS の URLopen を差し替えられる（_urlopen をモック可能）など、外部依存の差し替えポイントを提供。
  - ETL の各関数は id_token 注入や date_from 指定が可能でユニットテスト容易。
  - 環境変数自動ロードは必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Documentation / Logging
- 各モジュールに詳細な docstring を付与し設計意図・制約・戻り値を明記。
- 主要処理にログ（info/warning/exception）を埋め込み、運用時のトラブルシュートを支援。

### Known limitations / Notes
- strategy, execution, monitoring パッケージは名前空間のみを定義しており、具体的な戦略ロジックや実際の発注処理は別途実装が必要。
- quality モジュールの詳細実装は本コードからは読み取れないため、ETL パイプラインは quality の公開 API に依存する設計となっている。
- 現行の HTTP クライアントは urllib を用いて実装されているため、将来的に asyncio や高機能な HTTP ライブラリに置き換える余地あり。

---

開発・運用に関する追加の推測や、CHANGELOG の改訂を希望する箇所があれば教えてください。必要に応じて項目を増減・分割してより詳細な履歴を作成します。