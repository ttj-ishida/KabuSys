# CHANGELOG

すべての注目すべき変更点を記録します。慣例に従い、SemVer（MAJOR.MINOR.PATCH）を使用しています。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買・データプラットフォームの基礎機能を実装しました。以下は主な追加点と設計上の要点です。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージ初期公開。トップレベルで data / research / ai / monitoring / strategy / execution といったサブパッケージを公開。
  - __version__ を "0.1.0" に設定。

- 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .git または pyproject.toml を起点にプロジェクトルートを探索することで CWD に依存しない挙動を実現。
  - .env パーサーは以下をサポート/考慮:
    - `export KEY=val` 形式
    - シングル/ダブルクォートされた値内のバックスラッシュエスケープ
    - クォート無し値のインラインコメント判定（直前が空白またはタブの場合）
  - Settings クラスを公開（settings インスタンス）:
    - J-Quants, kabu ステーション, Slack, DB パスなど複数設定用プロパティ（必須項目は未設定時に ValueError を送出）
    - KABUSYS_ENV 的な環境（development / paper_trading / live）と LOG_LEVEL の検証メカニズム
    - duckdb/sqlite パスのデフォルトを data/ 以下に設定

- データプラットフォーム（kabusys.data）
  - calendar_management モジュール:
    - JPX カレンダー取得・保持ロジック
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日ユーティリティ
    - calendar_update_job: J-Quants からの差分取得と冪等保存処理（バックフィル／健全性チェック付き）
    - DB 未取得時の曜日ベースフォールバック（主に土日判定）
  - pipeline ETL（kabusys.data.pipeline）:
    - ETLResult データクラス（ETL 実行の集約結果・品質問題・エラー情報を保持）
    - 差分取得ロジック、バックフィル、品質チェック（quality モジュールとの連携を想定）
  - etl モジュールは ETLResult を再エクスポート

- 研究（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算（prices_daily 参照）
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率の計算
    - calc_value: PER（EPS が 0 や欠損時は None）、ROE（raw_financials 参照）
    - 各関数は DuckDB で SQL を用いて計算し (date, code) 単位の辞書リストを返す
  - feature_exploration モジュール:
    - calc_forward_returns: 将来リターン（任意ホライズン）を一括取得
    - calc_ic: スピアマンのランク相関（IC）計算（code マッチング・欠損行除外・最小レコード数チェック）
    - factor_summary: count/mean/std/min/max/median といった統計サマリー
    - rank: 平均ランク（ties は平均ランク）を返すユーティリティ
  - research の __all__ で主要関数をエクスポート

- AI（kabusys.ai）
  - news_nlp モジュール:
    - raw_news + news_symbols を銘柄毎に集約し、OpenAI（gpt-4o-mini、JSON mode）でセンチメントをスコア化
    - バッチ処理（最大 20 銘柄/チャンク）、1銘柄あたり記事数・文字数上限、レスポンス検証、スコアの ±1.0 クリップ
    - リトライ（429 / ネットワーク / タイムアウト / 5xx）を指数バックオフで実装。致命的でない失敗はスキップし処理継続（フェイルセーフ）
    - スコア書き込みは部分的に置換（該当 code の DELETE → INSERT）して部分失敗時の既存データ保護
    - calc_news_window: JST ベースの時間ウィンドウ計算（前日15:00 ～ 当日08:30 JST を UTC naive datetime で返す）
  - regime_detector モジュール:
    - ETF 1321（Nikkei 225 連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）の合成により日次マーケットレジーム（bull/neutral/bear）を判定
    - マクロニュース抽出、OpenAI 呼び出し、合成スコアのクリップ、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - LLM 呼び出し失敗時は macro_sentiment=0.0 として処理を継続（フェイルセーフ）
  - OpenAI との呼び出しは各モジュールで独立実装（モジュール間でプライベート関数を共有しない設計）
  - API キー解決は api_key 引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出

- その他
  - duckdb を利用する前提で各種テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar 等）を参照する実装
  - ロギング（logger）を各モジュールに配置し、情報・警告・例外を適切に記録する設計

### 変更（Changed）
- （初回リリースのため該当なし）

### 修正（Fixed）
- （初回リリースのため該当なし）

### 既知の設計/運用上の注意（Notes）
- OpenAI 呼び出しは外部サービスへ依存しており、API レート制限やネットワーク障害に備えたリトライ・フォールバックを備えていますが、API キーの有無や課金設定は運用側で管理してください。
- DuckDB の executemany で空リストを渡すと失敗するバージョン（0.10 系）への互換性考慮のため、書き込み前に params が空でないか確認するロジックを実装しています。
- .env の自動ロードはプロジェクトルート検出に基づくため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD で制御を推奨します。
- 時刻・日付は基本的に timezone を混入させない UTC naive または date オブジェクトで扱っています。JST/UTC の変換箇所は calc_news_window 等で明示的に扱っています。
- AI 出力のバリデーションでは JSON の前後ノイズが混じる場合に最外の {} を抽出する復元処理を実装していますが、生成される JSON の安定性は保証されないため運用ではモニタリングが必要です。

---

今後の予定（例）
- ETL のジョブランナー、品質チェックルールの拡充、モニタリング（Slack 通知）との連携
- strategy / execution / monitoring の具体的な注文・バックテスト機能拡充

（この CHANGELOG はコードベースの実装内容から推測して作成しました。実際のコミット履歴やリリースノートがある場合はそちらを優先して補完してください。）