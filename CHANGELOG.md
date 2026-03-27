# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在の日付: 2026-03-27

## [Unreleased]

## [0.1.0] - 2026-03-27
初回公開リリース。

### Added
- パッケージ基盤
  - パッケージ名: `kabusys`
  - バージョン: `0.1.0`
  - パッケージ公開時に利用するトップレベル __all__: `["data", "strategy", "execution", "monitoring"]`（各サブモジュールのうち一部は実装済み）

- 設定管理 (`kabusys.config`)
  - 環境変数/`.env` ファイルの自動読み込み機能を実装。
    - プロジェクトルート判定: `.git` または `pyproject.toml` を探索してルートを特定（カレントワーキングディレクトリに依存しない）。
    - 読み込み優先順位: OS環境変数 > `.env.local` > `.env`。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで自動ロードを無効化可能（テストでの利用を想定）。
  - `.env` パーサ実装の強化:
    - `export KEY=val` 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなしの行で `#` がコメントかどうかを空白直前で判定。
    - 無効行（空行、コメント、不正なキー行）は無視。
  - 環境変数取得ヘルパ `Settings` を提供:
    - 必須値取得 (`_require`) による未設定時の明確なエラー。
    - J-Quants / kabu-station / Slack / DB パスなどのプロパティを定義:
      - `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）、`SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
      - DB パス: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト: data/monitoring.db）
    - 実行環境判定: `KABUSYS_ENV`（development / paper_trading / live のいずれか）と `LOG_LEVEL` 検証。
    - ヘルパ: `is_live`, `is_paper`, `is_dev`

- AI 関連 (`kabusys.ai`)
  - ニュース NLP (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを評価し、`ai_scores` テーブルへ書き込む機能。
    - 特徴:
      - ニュース時間ウィンドウ計算（JST 基準：前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）。
      - 1銘柄あたり最大記事数・文字数でトリム（デフォルト: 10 件 / 3000 文字）。
      - バッチ送信（1 API 呼び出しあたり最大 20 銘柄）。
      - JSON Mode を利用した厳格なレスポンス検証。レスポンスの復元ロジック（前後余分テキストの最外側 {} 抽出）を実装。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフのリトライ。
      - スコアは ±1.0 にクリップして保存。
      - 書き込みは銘柄単位で DELETE → INSERT を行い、部分失敗時に既存スコアを保護。
      - テスト容易性のため `_call_openai_api` をモック可能に設計。
    - 公開関数: `score_news(conn: duckdb.Connection, target_date: date, api_key: str | None) -> int`
      - 成功時は書き込んだ銘柄数を返す。
      - API キー未設定時は ValueError を送出。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（Nikkei225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定・保存。
    - 処理概要:
      - 1321 の直近 200 日の終値から MA200 乖離を計算（ルックアヘッドバイアス対策で target_date 未満のデータのみ使用）。
      - マクロキーワードで raw_news をフィルタしてタイトルを抽出（最大 20 件）。
      - OpenAI（gpt-4o-mini）でマクロセンチメントを -1.0〜1.0 のスコアで取得（API 失敗時は 0.0 にフォールバック）。
      - 合成スコアを clip(-1,1) し閾値でラベル付け。
      - `market_regime` テーブルへ冪等的に（BEGIN / DELETE / INSERT / COMMIT）書き込み。
    - フェイルセーフ実装: LLM 呼び出し失敗やデータ不足時は中立（または macro_sentiment=0.0）で継続。
    - 公開関数: `score_regime(conn: duckdb.Connection, target_date: date, api_key: str | None) -> int`

- Data / ETL / カレンダー (`kabusys.data`)
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job(conn, lookahead_days=90)` を実装（J-Quants クライアントを利用して差分取得、冪等保存）。
    - 営業日判定ユーティリティ:
      - `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`
      - DB に値がない場合は曜日ベース（週末休）でフォールバック。
      - 探索範囲の上限（安全性）を設定して無限ループを防止。
  - ETL パイプライン (`kabusys.data.pipeline`) と ETL 結果型
    - ETL 実行結果を表現する `ETLResult` dataclass を提供（fetch/save カウント、品質問題一覧、エラー一覧を格納）。
    - パイプラインの設計方針を反映（差分更新、バックフィル、品質チェックの収集と継続処理）。
  - ETL 公開インターフェース (`kabusys.data.etl`) で `ETLResult` を再エクスポート。

- Research / 分析 (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - モメンタム、ボラティリティ、バリュー系の定量ファクターを DuckDB 上で算出する関数を実装:
      - `calc_momentum(conn, target_date)` : mom_1m / mom_3m / mom_6m / ma200_dev（データ不足時は None）。
      - `calc_volatility(conn, target_date)` : atr_20, atr_pct, avg_turnover, volume_ratio（ウィンドウ不足は None）。
      - `calc_value(conn, target_date)` : PER（EPS がない/0 の場合は None）、ROE（最新報告書ベース）。
    - 設計方針: DB（prices_daily / raw_financials）以外にアクセスせず、安全に計算。
  - 特徴量探索・統計 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons=[1,5,21])`（horizons のバリデーションを実施）。
    - Information Coefficient（Spearman の ρ）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（有効レコードが 3 件未満は None）。
    - ランキング補助: `rank(values)`（同順位は平均ランク）。
    - ファクター統計サマリー: `factor_summary(records, columns)`（count/mean/std/min/max/median を計算）。
    - research パッケージは `kabusys.data.stats.zscore_normalize` を再公開し、研究用関数群をまとめて提供。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Security
- 環境変数の取り扱いについて明示的な保護設計:
  - .env 読み込み時、既存 OS 環境変数を protected として上書きを防止（`.env.local` は override=True だが protected を尊重）。

### Notes / 設計上の留意点
- ルックアヘッドバイアス対策:
  - ai モジュール（news_nlp, regime_detector）および research モジュールは内部で datetime.today() / date.today() を直接参照せず、必ず呼び出し側から `target_date` を受け取る設計。
- フェイルセーフ:
  - LLM/API の一時障害やレスポンスパース失敗は例外を投げずにログ出力して中立的な値へフォールバックする箇所がある（運用中の一部処理継続を重視）。
- DuckDB を中心とした設計:
  - ほとんどの処理は DuckDB 接続を受け取り SQL と Python 組合せで完結するよう設計。
- テスト容易性:
  - OpenAI 呼び出しを隠蔽した `_call_openai_api` を各モジュールで用意しており、ユニットテストでモック差し替え可能。
- 未実装 / 将来的な実装予定:
  - トップレベル __all__ に含まれる `strategy`, `execution`, `monitoring` の実装はこのリリース時点でソース内に見当たらないため、今後追加予定。

---

（この CHANGELOG はソースコードから推測して作成しています。実際のコミット履歴やリリースノートとは差異がある可能性があります。）