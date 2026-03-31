# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」準拠です。  
初回リリース相当のコードベース内容から推測して作成しています。

## [Unreleased]

（現在未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初回リリース想定の機能群と実装ノート。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは `0.1.0` に設定。
  - パッケージ公開用のトップレベル exports を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を読み込む自動読み込みを実装。
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロード無効化可能（テスト向け）。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に行い、CWD に依存しない実装。
  - .env パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供し、利用可能な設定プロパティを公開:
    - J-Quants: `jquants_refresh_token`（必須）
    - kabuステーション: `kabu_api_password`, `kabu_api_base_url`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `slack_bot_token`, `slack_channel_id`（必須）
    - データベースパス: `duckdb_path`（デフォルト: data/kabusys.duckdb）、`sqlite_path`（デフォルト: data/monitoring.db）
    - 実行環境判定: `env`（development, paper_trading, live のいずれかの検証あり）、`log_level`（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証あり）、および `is_live`/`is_paper`/`is_dev` 補助プロパティ。
  - 必須環境変数未設定時は ValueError を送出する挙動。

- データプラットフォーム（DuckDB ベース）
  - データ ETL 用インターフェースと結果表現:
    - `kabusys.data.pipeline.ETLResult` を実装し、ETL の取得数・保存数・品質問題・エラー要約を保持。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - 市場カレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間更新ジョブ（`calendar_update_job`）を実装。J-Quants クライアント経由で差分取得し冪等保存。
    - 営業日判定・探索ユーティリティを提供:
      - `is_trading_day`, `is_sq_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`
    - DB にカレンダーデータがない場合は曜日ベース（土日除外）でのフォールバック実装。
    - 最大探索範囲やバックフィル、健全性チェック（未来日付の異常検出）など運用考慮を実装。
  - DuckDB 用ユーティリティ:
    - テーブル存在チェック、日付変換などの内部ユーティリティを提供。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum ファクター: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）
    - Volatility / Liquidity: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率
    - Value ファクター: PER（EPS が 0 または欠損時は None）、ROE（raw_financials から採取）
    - 各関数は DuckDB の `prices_daily` / `raw_financials` を参照し、(date, code) をキーとする dict リストを返す。
    - データ不足時は None を返す等の堅牢性考慮。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: `calc_forward_returns`（デフォルト horizons=[1,5,21]、複数 horizon を1クエリで取得）
    - IC（Information Coefficient）計算: `calc_ic`（Spearman ランク相関）
    - ランク化ユーティリティ: `rank`（同順位は平均ランク）
    - 統計サマリー: `factor_summary`（count/mean/std/min/max/median）
    - 実装は外部ライブラリに依存せず標準ライブラリと DuckDB を使用。

- AI / NLP モジュール (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`kabusys.ai.news_nlp`)
    - raw_news / news_symbols テーブルから銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON mode へバッチ送信して銘柄ごとのスコアを算出。
    - タイムウィンドウ: JST 前日 15:00 ～ 当日 08:30（内部は UTC naive で計算）。`calc_news_window` を提供。
    - バッチサイズ、最大記事数、文字数上限などトークン肥大化対策を実装。
    - 429（レート制限）・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンス検証 `_validate_and_extract` により JSON パース、results リスト、code/score の妥当性、スコアの数値性を検証。スコアは ±1.0 にクリップ。
    - 成功したスコアのみを ai_scores テーブルへ置換（DELETE → INSERT）し、部分失敗時に既存スコアを保護する戦略を採用。
    - `score_news` が公開 API（conn, target_date, api_key）を提供。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（日本、米国・グローバルのキーワードリストを実装）。
    - OpenAI 呼び出しで JSON レスポンスをパースし macro_sentiment を算出。API エラー時は macro_sentiment=0.0 で継続。
    - レジームスコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) により計算し、閾値でラベル付け。
    - 結果は `market_regime` テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）する設計。
    - `score_regime` が公開 API（conn, target_date, api_key）を提供。
  - OpenAI クライアント呼び出しは各モジュール内で独立して実装されており、テストで差し替え可能（unittest.mock.patch を想定）。

- ロギング・運用設計
  - 多くの箇所で適切な logger を使用して情報・警告・例外を記録。
  - 重要処理（DB 書き込み等）はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護。
  - ルックアヘッドバイアス防止のため、各スコアリング関数は内部で datetime.today()/date.today() を直接参照せず、必ず caller が `target_date` を提供する設計。

### 変更 (Changed)
- （初版のため特になし）

### 修正 (Fixed)
- （初版のため特になし）

### セキュリティ・運用に関する注意点 (Security / Ops)
- OpenAI API キーは引数で注入可能（テスト容易化）／環境変数 `OPENAI_API_KEY` を参照。
- 自動で .env を読み込む挙動はテストで無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- .env ファイルの読み込み失敗は警告を出し処理継続（例外は投げない）。
- DB 書き込み失敗時は ROLLBACK を試み、ROLLBACK 自体が失敗した場合は警告ログを出す。

### 既知の制約 / 今後の作業候補 (Known issues / TODO)
- 一部機能は J-Quants クライアント（外部モジュール）に依存しているため、実運用前に API キーやネットワーク設定の検証が必要。
- ai モジュールは OpenAI のレスポンス形式に依存するため、将来の SDK 変更への追従が必要（現在は JSON mode を利用）。
- PBR や配当利回り等のバリューファクターは未実装（将来追加予定）。
- DuckDB バインドの互換性（executemany の空リスト等）を考慮した実装があるが、運用中に DB バージョン依存の問題が出る可能性がある。

---

（注）本 CHANGELOG は与えられたコードから推測して作成した初回リリース想定の変更履歴です。実際のリリースノート作成時はコミット履歴やリリース要件に基づき適宜補正してください。