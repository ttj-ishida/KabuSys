# Changelog

すべての notable な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
過去の日付やバージョンは、ソースから推測した初期リリース内容を基に作成しています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初期リリース。本バージョンではデータ収集・前処理、リサーチ用ファクター計算、LLM を用いたニュースセンチメント評価と市場レジーム判定、及び運用周りのユーティリティを実装しています。

### Added
- パッケージ基礎
  - kabusys パッケージの公開モジュール群を定義（data, strategy, execution, monitoring）。
  - パッケージバージョンを `0.1.0` に設定。

- 設定管理 (`kabusys.config`)
  - .env / .env.local の自動ロード（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - 自動ロードを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - .env パーサーは `export KEY=val` 形式、クォート（シングル/ダブル）やエスケープ、インラインコメントの取り扱いに対応。
  - 必須環境変数取得用の `Settings` クラスを提供（J-Quants・kabuAPI・Slack・DBパス等のプロパティを含む）。
  - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- データプラットフォーム（DuckDB ベース）
  - calendar_management
    - JPX 市場カレンダーの管理・夜間差分更新ジョブ（J-Quants からの取得を想定）。
    - 営業日判定 (is_trading_day)、前後営業日取得 (next_trading_day / prev_trading_day)、期間内営業日取得 (get_trading_days)、SQ日判定 (is_sq_day) を実装。
    - カレンダー未取得時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェックを導入。
  - ETL / pipeline
    - ETL 実行結果を表現する `ETLResult` データクラス（品質チェック結果・エラー情報含む）を実装し、外部公開。
    - 差分取得、バックフィル、品質チェックの設計に基づくユーティリティ関数群（内部ユーティリティとしてテーブル存在確認や最大日付取得等）。
    - jquants_client と連携しての差分取得 / 保存処理を想定（保存は idempotent を想定）。

- AI（LLM）関連
  - kabusys.ai.news_nlp
    - ニュース記事（raw_news, news_symbols）を銘柄別に集約し、OpenAI（gpt-4o-mini、JSON mode）にバッチ送信してセンチメント（-1.0〜1.0）を算出。
    - 1銘柄当たり最大記事数・文字数トリム、最大バッチサイズ、チャンクごとのリトライ（429・ネットワーク・タイムアウト・5xx 対応）を実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code の正規化、数値チェック、スコアクリップ）を実装。
    - DuckDB の executemany の制約を考慮した書込み（部分成功時に既存スコアを保護する DELETE→INSERT ロジック）。
    - API キーの注入可（テスト容易性）と、未設定時は ValueError を送出。
    - LLM 呼び出し部分はテストで差し替え可能（_call_openai_api の patch を想定）。

  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み70%）と、ニュース由来のマクロセンチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し `market_regime` テーブルへ書き込み。
    - prices_daily からの MA 計算、raw_news からマクロキーワードでの絞り込み、OpenAI によるマクロセンチメント評価（JSON mode）を実装。
    - API エラー・パースエラー時は macro_sentiment=0.0 にフォールバックするフェイルセーフ。
    - 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK とログ出力。

- リサーチ・ファクター群 (`kabusys.research`)
  - factor_research
    - モメンタム: mom_1m / mom_3m / mom_6m、200日MA乖離 (ma200_dev) を計算。
    - ボラティリティ/流動性: 20日 ATR、相対ATR (atr_pct)、20日平均売買代金、出来高比率を計算。
    - バリュー: PER（EPS が 0 / 欠損時は None）、ROE を raw_financials と prices_daily から算出。
    - SQL + Python ベースで DuckDB 上に実行、外部 API 呼び出しなし、出力は (date, code) キーの辞書リスト。
  - feature_exploration
    - 将来リターン計算（horizons: デフォルト [1,5,21]、最大252営業日上限）。
    - IC（Information Coefficient）計算：Spearman のランク相関（ランク付けは同順位平均ランク実装）。
    - factor_summary: count/mean/std/min/max/median を算出（None を除外）。
    - 全体的に pandas 等に依存せず標準ライブラリで実装。

- テスト・運用上の配慮
  - ルックアヘッドバイアス対策として各処理は datetime.today()/date.today() を参照しない、呼び出し側から target_date を注入する設計。
  - OpenAI 呼び出しはリトライ（指数バックオフ）と明示的な例外ハンドリングを実装。
  - 各所でログ出力を充実させ、障害時は警告/例外ログを記録する（ROLLBACK の失敗も警告ログ）。

### Fixed
- 該当なし（初期リリースのため bugfix エントリはなし）。

### Changed
- 該当なし（初期リリースのため変更履歴はなし）。

### Deprecated
- 該当なし。

### Security
- API キーやパスワードは環境変数経由で管理する設計（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY、SLACK_BOT_TOKEN 等）。.env 自動ロード機能は OS 環境変数を保護する仕組みを利用（.env 上書き制御）。

### 注意事項 / 既知の制限
- DuckDB への依存があり、一部実装は DuckDB のバージョン互換性（executemany の空リスト等）を考慮した実装になっています。
- OpenAI（gpt-4o-mini）への依存があり、API キー未設定時は処理が例外となります（明示的なエラーを返す）。
- LLM 結果のパースや API 障害に対してはフォールバック（スコア 0.0、スキップ等）を用意しているため、部分失敗が全体停止に繋がりにくい設計です。
- news_nlp / regime_detector の LLM 呼び出しロジックはモジュール間で意図的に分離されており、テスト時は差し替えが可能です。

---

参考: 実装に現れる主要な環境変数
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- DUCKDB_PATH, SQLITE_PATH
- KABUSYS_ENV (development / paper_trading / live), LOG_LEVEL
- OPENAI_API_KEY

（以上）