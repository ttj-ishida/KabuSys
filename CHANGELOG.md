# Changelog

すべての注目すべき変更点をここに記録します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。  

最新更新日: 2026-03-31

## [0.1.0] - 2026-03-31
初回公開リリース。

### Added
- パッケージ基盤
  - 新規パッケージ `kabusys` を追加。公開 API はパッケージルートで `__version__ = "0.1.0"` として管理。
  - `__all__` に "data", "strategy", "execution", "monitoring" を指定（各サブパッケージは順次実装想定）。

- 設定 / 環境変数管理 (`kabusys.config`)
  - `.env` / `.env.local` の自動ロード機能を追加。プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出（カレントワーキングディレクトリに依存しない）。
  - `.env` パーサを強化:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - インラインコメントの取り扱い（クォート外で `#` の直前が空白/タブの場合をコメントと認識）。
    - 無効行（空行、コメント行、`key=value` でない行）は無視。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により無効化可能（テスト用途）。
  - 環境変数取得ユーティリティ `Settings` を追加。必須キー取得時に未設定なら `ValueError` を投げる（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 等）。
  - `KABUSYS_ENV` のバリデーション（development / paper_trading / live）と `LOG_LEVEL` バリデーションを実装。
  - DuckDB / SQLite のデフォルトパス設定（`DUCKDB_PATH`, `SQLITE_PATH`）。

- AI 関連 (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp.score_news`)
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini, JSON mode）へバッチ送信してスコアを算出、`ai_scores` テーブルへ書き込み。
    - バッチサイズ、1銘柄あたりの最大記事数・文字数トリム、タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を実装。
    - レート制限（429）・ネットワーク断・タイムアウト・5xx を指数バックオフでリトライ。その他のエラーはスキップ（フェイルセーフ設計）。
    - レスポンスの厳密バリデーション（JSONパース、keys/型検査、未知コードの無視、スコア数値・有限性検査）。スコアは ±1.0 にクリップ。
    - DuckDB への書き込みは部分置換（指定コードのみ DELETE → INSERT）して部分失敗時に既存スコアを保護。DuckDB executemany の空リスト制約を考慮。
    - テストしやすさのため `_call_openai_api` をモック可能に設計。
  - 市場レジーム判定 (`kabusys.ai.regime_detector.score_regime`)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull' / 'neutral' / 'bear' を判定し、`market_regime` テーブルへ冪等書き込み。
    - マクロニュース抽出（マクロキーワード群）、OpenAI 呼び出し（gpt-4o-mini, JSON mode）、リトライ/バックオフ、API失敗時のフォールバック（macro_sentiment = 0.0）、ルックアヘッドバイアス対策（target_date 未満のデータのみ使用）を実装。
    - OpenAI クライアントは API キー引数または環境変数 `OPENAI_API_KEY` から解決。未設定時は `ValueError` を送出。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算関数を実装:
    - `calc_momentum`: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None を返す）。
    - `calc_volatility`: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率。
    - `calc_value`: raw_financials からの EPS/ROE 組合せで PER/ROE を算出。
  - 特徴量探索ユーティリティ:
    - `calc_forward_returns`: 指定 horizon（営業日ベース）の将来リターンを同一クエリで取得。
    - `calc_ic`: ランク相関（Spearman 相当）を計算。3 件未満で計算不能なら None。
    - `rank`: 平均ランク（同順位は平均 rank）を算出。
    - `factor_summary`: count/mean/std/min/max/median を算出する統計サマリー。
  - `kabusys.data.stats.zscore_normalize` を再エクスポート。

- データプラットフォーム (`kabusys.data`)
  - マーケットカレンダー管理 (`calendar_management`)
    - `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` 等の営業日判定ロジックを実装。
    - DB の `market_calendar` を優先し、未登録日は曜日（週末）ベースのフォールバックを提供。探索時の最大日数上限設定で無限ループを防止。
    - 夜間バッチ `calendar_update_job` を追加（J-Quants API から差分取得、バックフィル、健全性チェック、idempotent 保存）。
  - ETL / パイプライン (`pipeline`, `etl`)
    - ETL 処理の結果を表現する `ETLResult` dataclass を公開。
    - 差分取得・保存・品質チェックの方針に沿った実装（J-Quants クライアント呼び出しを想定）。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得、取得範囲調整など。
  - jquants_client を通じた外部 API 連携を想定（実際のクライアント実装は分離）。

- 汎用
  - DuckDB を主要な分析 DB として利用。SQL と Python の組合せで処理を実装。
  - トランザクション処理（BEGIN / DELETE / INSERT / COMMIT）と例外発生時の ROLLBACK 保障。ROLLBACK 失敗時のログ出力を追加。
  - ロギングを細かく追加し、処理状況やフォールバックを記録。

### Changed
- （初回リリースのため該当なし）

### Fixed
- DuckDB 互換性に配慮し、`executemany` に空リストを渡さないようにガードを追加（DuckDB 0.10 の制約対応）。
- OpenAI レスポンスパースや API エラー時の取り扱いを堅牢化（JSON 付随テキストの復元、status_code が存在しない場合の安全対応、非 5xx の APIError は即スキップ等）。

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- API キーやトークンは環境変数経由で管理する設計。必須の環境変数が未設定の場合は起動時に検出して例外を投げる（安全性向上）。
- `.env` 自動ロード機能は OS 環境変数を保護するため `protected` キーセットを用いて上書きを防止する実装。

### Notes / Limitations
- OpenAI API（gpt-4o-mini）利用部分は外部 API 呼び出しを伴うためコストが発生します。API キーと利用制限に注意してください。
- strategy / execution / monitoring の具体的な発注ロジックや外部注文 API 連携は本スナップショットでは含まれていない（パッケージの公開 API に名称は存在するが実装は別途）。
- DuckDB に依存した SQL 実装のため、互換性やバージョン差異（特にリスト型バインド等）に注意。
- テスト容易性を考慮し、OpenAI 呼び出し箇所はモックで差し替え可能に設計されている。

---

今後のリリースでは、実取引向け execution 層、戦略定義のエクスポート、監視/アラート機能（Slack 連携等）の拡張やドキュメント整備を予定しています。