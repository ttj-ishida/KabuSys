# Changelog

すべての notable な変更点をこのファイルに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニング (MAJOR.MINOR.PATCH) に従います。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-04

初回リリース。日本株自動売買システムのコアライブラリを公開します。主な機能・設計上のポイントは以下の通りです。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化とバージョン情報（__version__ = "0.1.0"）。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__）。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能（プロジェクトルート自動検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
  - export KEY=val、クォート、インラインコメント等に対応した .env パーサー。
  - Settings クラスを提供し、アプリケーション設定をプロパティとして取得可能:
    - JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL などの必須/任意設定
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）
    - 監視用ファイルパス（PID_FILE_PATH / KILL_FLAG_PATH）や閾値（CPU/MEMORY/DISK）
    - 環境種別（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション
    - is_live / is_paper / is_dev の簡易フラグ

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を元に銘柄別ニュースを集約し、OpenAI（gpt-4o-mini）の JSON モードでセンチメント評価を実施。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC換算で前日 06:00 ～ 23:30）を対象にする calc_news_window 提供。
  - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数のトリム（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフ実装。
  - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
  - ai_scores テーブルへの冪等書き込み（DELETE → INSERT、部分失敗時に他コードを保護）。
  - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み件数を返す。APIキー未設定時は ValueError。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を算出。
  - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（最大 20 記事）とリトライ/フォールバックロジック。
  - ルックアヘッドバイアス対策（target_date 未満のデータのみ使用、datetime.today() を参照しない）。
  - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - 公開 API: score_regime(conn, target_date, api_key=None) — 成功時に 1 を返す。APIキー未設定時は ValueError。

- リサーチ / ファクター計算（kabusys.research）
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離等を計算（prices_daily 参照）。
  - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率等を計算。
  - calc_value: PER（EPS の存在確認あり）、ROE を raw_financials と prices_daily から算出。
  - feature_exploration: calc_forward_returns（任意ホライズンで将来リターンを一括取得）、calc_ic（Spearmanランク相関でIC算出）、factor_summary（基本統計量）、rank（同順位は平均ランク）。
  - 全関数は DuckDB 接続を受け取り、外部 API・本番発注にはアクセスしない設計。
  - 計算上の安全策（データ不足時は None、horizons の入力バリデーション等）。

- データプラットフォーム（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理／営業日判定ユーティリティを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。
    - market_calendar データがない場合は曜日ベースでフォールバック（土日非営業）。
    - カレンダーデータの夜間バッチ更新 job（calendar_update_job）を提供。J-Quants クライアント経由で差分取得し冪等保存。
    - 最大探索日数・バックフィル・健全性チェック等を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを提供（取得数・保存数・品質問題・エラー集約）。
    - 差分更新、バックフィル、品質チェックの設計方針を実装（jquants_client / quality との連携前提）。
  - etl モジュールで ETLResult を再エクスポート。

### Fixed / Compatibility
- DuckDB 0.10 系の executemany 空リストバインド制約への互換性対応:
  - ai_scores への書き込み時に executemany に空リストを渡さないよう保護ロジックを追加（空時は呼ばない）。
  - 同様の互換性ケアを複数箇所で実装。

### Security / Safety
- OpenAI API 呼び出し失敗時のフォールバック動作を明確化:
  - news/regime の API エラーやパース失敗時は例外を上位に伝播させず、フェイルセーフ値（macro_sentiment=0.0、スコア取得スキップ等）で継続する設計。
- 環境変数の必須チェックとバリデーションにより、誤設定時に早期にエラーを通知。

### Design notes / その他重要事項
- ルックアヘッドバイアス防止のため、全ての「日付ベースの処理」は datetime.today()/date.today() に依存せず、呼び出し側が target_date を指定する設計。
- OpenAI の JSON Mode を使用し、レスポンスは厳密な JSON を想定。パース失敗時の復元処理（最外の {} を抽出）を実装。
- ロギング（logger）を各モジュールに導入し、警告・情報を適切に出力。
- 各種重み、閾値、バッチサイズ等は定数化されパラメータ調整可能。

## Notes for users
- OpenAI API キー（OPENAI_API_KEY）が必要な機能:
  - kabusys.ai.score_news, kabusys.ai.score_regime（api_key 引数で注入可能）。
- .env 自動読み込みはプロジェクトルートの特定が前提。配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB をローカルで利用する想定（デフォルト DUCKDB_PATH = data/kabusys.duckdb）。既存 DB スキーマに依存します。

---

作成: kabusys コードベース（初回リリース 0.1.0）に基づく推定 CHANGELOG。