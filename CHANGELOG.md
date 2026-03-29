# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

## [0.1.0] - 2026-03-29

初回公開リリース。以下の主要機能・モジュールを追加しました。

### 追加
- パッケージ基本
  - kabusys パッケージを追加。公開 API として data, research, ai, execution, monitoring（__all__）を定義。
  - バージョンを `0.1.0` に設定。

- 環境設定（kabusys.config）
  - .env / .env.local の自動ロード機能を実装（OS 環境変数 > .env.local > .env の優先度）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない .env 検出。
  - .env 行パーサ（export KEY=val、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い）を実装。
  - OS 環境変数を保護する protected 機能（.env.local の上書き時に既存 OS 環境を保護）。
  - Settings クラスを公開（プロパティ経由で必要な設定を取得）。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - Slack 関連: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - ヘルパー: is_live / is_paper / is_dev

- AI（kabusys.ai）
  - ニュース NLP スコアリング（news_nlp.score_news）
    - 指定日（target_date）に対応するニュース収集ウィンドウ計算（calc_news_window）。
    - raw_news と news_symbols を集約し、銘柄ごとに最大記事数・文字数でトリムして LLM に送信。
    - バッチ処理（1API呼び出しあたり最大 20 銘柄）・JSON モードでの OpenAI 呼び出し。
    - リトライ（429/ネットワーク断/タイムアウト/5xx）を指数バックオフで実装。
    - レスポンスのバリデーションロジック（JSON 抽出、results 配列、code/score の検証、数値変換、±1.0 クリップ）。
    - idempotent な DB 書き込み（DELETE → INSERT のトランザクション）で ai_scores を更新。部分失敗で既存データを保護。
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして処理継続（例外を全体に波及させない）。
    - テスト容易性: OpenAI 呼び出し部分をモンキーパッチ（unittest.mock.patch）で差し替え可能に設計。

  - 市場レジーム判定（regime_detector.score_regime）
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - ma200_ratio の計算（ルックアヘッド回避: target_date 未満のデータのみ使用）。
    - マクロ記事抽出（タイトルベース、キーワード群でフィルタ）。
    - OpenAI によるマクロセンチメント評価（gpt-4o-mini、JSON モード）とリトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - スコア合成、閾値に基づくラベリング、market_regime への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - テスト容易性: OpenAI 呼び出しはモジュール内で完結（news_nlp と内部実装を共有しない設計）。

- データ基盤（kabusys.data）
  - ETL パイプライン（data.pipeline）
    - ETLResult データクラス（target_date, fetched/saved counts, quality_issues, errors 等）を実装し公開。
    - 差分取得、バックフィル（日数指定）、品質チェック統合、jquants_client 経由の idempotent 保存を想定した設計。
    - DuckDB での最大日付取得やテーブル存在チェックなどユーティリティを実装。
  - カレンダー管理（data.calendar_management）
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データがない場合は曜日ベース（平日）でのフォールバック。
    - next/prev_trading_day は最大探索日数制限（デフォルト 60 日）で無限ループを防止。
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得して保存、バックフィルと健全性チェックを実施。
  - ETL インターフェース（data.etl）で ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）、データ不足時の None 扱い。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を算出（EPS が無効な場合は None）。PBR/配当利回りは未実装として明記。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API にはアクセスしない設計。
  - 特徴量探索（research.feature_exploration）
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズン検証（正の整数かつ <=252）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足（<3 レコード）では None を返す。
    - rank: 同順位は平均ランクにするランク付け実装（浮動小数の丸め対策あり）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を算出。
    - 実装は pandas 等に依存せず標準ライブラリ + DuckDB SQL を利用。

### 改善 / 設計方針
- ルックアヘッドバイアス対策
  - AI（news_nlp/regime_detector）および ETL/リサーチ関数は内部で datetime.today()/date.today() を参照しない設計。呼び出し側が target_date を渡すことで過去データのみを利用。
  - prices_daily クエリには target_date 未満 / 以降の排他条件を明示してルックアヘッドを防止。

- OpenAI 呼び出しの堅牢化
  - JSON モードでの呼び出し、厳密なレスポンスバリデーション、リトライ（429/ネットワーク/5xx/タイムアウト）と指数バックオフを実装。
  - API 失敗時はフェイルセーフ（0.0 やスキップ）で処理継続。テストのために API 呼び出し点を差し替え可能。

- DuckDB 互換性と安全な SQL
  - executemany に空リストを渡さないガード、list 型バインドの回避（個別 DELETE 実行）など、DuckDB バージョン差異に対する配慮。
  - date 値の変換ユーティリティ（_to_date）を追加。

- トランザクションと冪等性
  - market_regime や ai_scores への書き込みは DELETE → INSERT のトランザクションで冪等性を確保。書き込み失敗時は ROLLBACK を試み、ROLLBACK 失敗時は警告ログを出力。

### 修正 / 既知の制約
- calc_value: PBR・配当利回りは現バージョンで未実装（ドキュメントに明記）。
- news_nlp / regime_detector: LLM レスポンスの形式変化やモデル差異に対してはパースエラーでスキップする設計。外部 API の挙動に依存するため、環境に応じたキー設定・レート制御が必要。
- calendar_update_job: J-Quants API や jquants_client の実装依存。API エラー時は 0 を返してジョブを安全に終了。
- .env パーサは一般的なシェル形式に対応するが、極端に複雑なエスケープや改行を含む値等は想定外の振る舞いとなる可能性あり。

### テスト／デバッグに関する拡張点
- OpenAI 呼び出し点（_call_openai_api）はユニットテスト時に patch して置き換え可能に実装。
- ログ出力を多用し、処理経過や異常ケースの追跡を容易に。

---

このリリースは初期実装として以下を目的としています:
- データ取得・カレンダー管理・ETL の基盤を整備
- 研究用ファクター計算と特徴量探索の提供
- ニュース NLP とマクロセンチメントを使った市場レジーム判定の PoC
- 運用環境での堅牢性（トランザクション、リトライ、フェイルセーフ）を重視

今後の予定（例）
- モデルの安定化・評価（LLM プロンプト改善、スコア検証）
- 追加ファクター（PBR、配当利回り等）
- パフォーマンス改善（大規模データ処理時の最適化）
- jquants_client / kabuステーション連携の拡充（実運用に向けた監視・発注機能）

（この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートはビルド・デプロイ時の変更やコミット履歴に基づいて調整してください。）