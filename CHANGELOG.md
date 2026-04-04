# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

注: この CHANGELOG はリポジトリ内のソースコードから推測して作成しています（実装上の意図・設計方針を要約）。実際の変更履歴が別にある場合は適宜差し替えてください。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-04

初回リリース（ベース実装）。主要な機能群と設計上の重要点を含みます。

### 追加 (Added)

- パッケージ基盤
  - `kabusys` パッケージの初期公開。パッケージバージョンは `0.1.0`。
  - エクスポート: data, strategy, execution, monitoring（__all__）。

- 設定 / 環境処理
  - `kabusys.config.Settings` による環境変数取得 API を提供。
  - .env 自動ロード機能:
    - プロジェクトルートを `.git` または `pyproject.toml` から探索して `.env` / `.env.local` を自動読み込み。
    - 読み込み優先順位: OS 環境 > .env.local（override）> .env（非 override）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化に対応（テスト用）。
  - .env パースの堅牢化:
    - `export KEY=val` 形式、クォート中のバックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
  - 必須変数検出: `_require` により未設定時は `ValueError` を送出。
  - 設定項目（例）:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`
    - LINE Messaging: `LINE_CHANNEL_ACCESS_TOKEN`, `LINE_USER_ID`
    - DB パス: `DUCKDB_PATH`, `SQLITE_PATH`
    - 実行監視: PID/KILL フラグ、CPU/メモリ/ディスク閾値
    - 実行環境フラグ: `KABUSYS_ENV`（development/paper_trading/live）、`LOG_LEVEL`

- データプラットフォーム（DuckDB ベース）
  - ETL パイプライン基盤:
    - `kabusys.data.pipeline.ETLResult` を公開（ETL 実行結果の dataclass）。
    - 差分取得・バックフィル・品質チェックを想定した設計（J-Quants API 統合を想定）。
  - カレンダー管理:
    - `kabusys.data.calendar_management` にて JPX カレンダー管理ロジックを実装。
    - 営業日判定（is_trading_day）、翌/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日列挙（get_trading_days）、SQ 判定（is_sq_day）を提供。
    - market_calendar を利用し未取得日は曜日ベースでフォールバックする堅牢な挙動。
    - 夜間バッチ更新ジョブ（calendar_update_job）を実装し J-Quants クライアント経由での差分フェッチ／冪等保存を行う。
  - DuckDB 互換性を考慮した実装上の注意:
    - executemany の空リスト制約に配慮したガードロジック等を導入。

- 研究（Research）モジュール
  - ファクター計算: `kabusys.research.factor_research`
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率
    - Value: PER（price / EPS）、ROE（raw_financials からの直取得）
    - 各関数は DuckDB 接続を受け取り prices_daily / raw_financials を参照する純粋計算実装
  - 特徴量探索: `kabusys.research.feature_exploration`
    - 将来リターン計算（calc_forward_returns、任意ホライゾン対応）
    - IC（Information Coefficient）計算（Spearman ランク相関）
    - ランク変換（rank）、統計サマリー（factor_summary）
  - 研究ユーティリティの再エクスポート:
    - `kabusys.research.__init__` で zscore_normalize（data.stats）等を公開

- AI（自然言語処理 / LLM 統合）
  - ニュース NLP（銘柄ごとのセンチメント）
    - `kabusys.ai.news_nlp.score_news` を提供：
      - 前日 15:00 JST ～ 当日 08:30 JST 相当のニュースウィンドウを計算（UTC 変換済み）。
      - raw_news と news_symbols から銘柄ごとに最新記事を集約し、最大 20 銘柄バッチで OpenAI（gpt-4o-mini、JSON-mode）へ送信。
      - レスポンス検証（JSON 抽出、results 配列、code/score 検証）、スコアを ±1.0 にクリップして ai_scores テーブルへ冪等書込（DELETE → INSERT）。
      - リトライ戦略（429・ネットワーク断・タイムアウト・5xx に対して指数バックオフ）。
      - API 呼び出し部分はテスト容易性のため差し替え可能（_call_openai_api を unittest.mock.patch）。
  - 市場レジーム判定
    - `kabusys.ai.regime_detector.score_regime` を提供：
      - ETF 1321（日経225 連動）200 日 MA 乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成しレジーム（bull/neutral/bear）を日次判定。
      - マクロ記事抽出は news_nlp.calc_news_window と連携し、キーワードベースでフィルタ。
      - OpenAI（gpt-4o-mini）で JSON レスポンスを期待、リトライ・フェイルセーフを実装（API 失敗時は macro_sentiment=0.0）。
      - DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。失敗時は ROLLBACK を試行。

### 変更 (Changed)

- 設計上の重要方針（初期実装段階からの明示）
  - ルックアヘッドバイアス防止のため、各処理は datetime.today()/date.today() を参照せず、明示的な target_date を受け取る設計。
  - DB 書き込みは冪等性を重視（既存レコードの削除→再挿入など）。
  - API 呼び出し失敗時は例外を破壊的に投げるのではなく、フェイルセーフで継続する箇所を多く採用（部分失敗での他データ保護）。
  - OpenAI 呼び出しのレスポンスは JSON-mode を想定しつつ、余計な前後テキストに対する復元ロジックを実装。

### 修正 (Fixed)

- 実装上の堅牢化:
  - .env パースにおけるクォート内エスケープ・インラインコメント処理、export プレフィックス対応を追加。
  - OpenAI レスポンスのパース失敗や API エラーでログを出力し安全にフォールバックする処理を多数追加。
  - DuckDB の executemany 空リスト制約を回避するガードを追加（ETL / ai_scores 書き込みなど）。

### 既知の注意点 (Notes)

- OpenAI API
  - `OPENAI_API_KEY`（または各 API 関数の api_key 引数）を必須とする処理がある。未設定時は ValueError を送出する。
  - 使用モデルは gpt-4o-mini。JSON-mode（response_format={"type": "json_object"}）を使うことを前提にしているが、現実の SDK 挙動や将来の変更に対して冗長にパースするロジックを含む。
- 外部依存
  - DuckDB をデータ格納に使用する設計。raw_news / prices_daily / ai_scores / market_regime / market_calendar / raw_financials 等のテーブルスキーマが前提。
  - J-Quants クライアント（jquants_client）との連携を想定（calendar_update_job / pipeline が呼び出す）。
- テスト支援
  - LLM API 呼び出しは内部関数をモック可能（unit テストでの差し替えを想定）。

### セキュリティ (Security)

- セキュリティ関連のリリース修正は含まれていません。機密情報（API キー等）は環境変数で管理することを推奨します。

---

今後のリリース案としては、以下が想定されます（例）:
- ユーザー向け CLI / サービス起動スクリプトの追加
- strategy / execution / monitoring の実装拡充（現状はパッケージ構成のみ）
- テストカバレッジ強化、CI ワークフロー定義
- スキーマ定義・マイグレーションツールの追加

必要であれば、この CHANGELOG の英訳版や、実際のコミット履歴をもとにしたより詳細な変更点追記を行います。