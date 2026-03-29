# Changelog

すべての変更は Keep a Changelog の方針に従っています。  
このファイルはコードベースから推測して作成した初期リリースの変更履歴です。

※ バージョン番号はパッケージ定義（src/kabusys/__init__.py の __version__）に合わせてあります。

## [Unreleased]

（現在なし）

## [0.1.0] - 2026-03-29

初期リリース

### 追加 (Added)
- パッケージ初期構成
  - パッケージ名: kabusys
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ に指定）

- 環境設定 / ロード機構（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数の統合読み込みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（__file__ を起点）。
  - 行パーサ: export 構文、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 既存 OS 環境変数を保護するための上書き制御（override / protected）。
  - Settings クラスを提供（プロパティで必要な環境変数を取得）
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - DUCKDB_PATH / SQLITE_PATH の既定値と Path 変換。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）と is_live/is_paper/is_dev ユーティリティ。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を集約して銘柄ごとに OpenAI（gpt-4o-mini）でセンチメントを算出し、ai_scores テーブルへ保存する score_news を実装。
  - ニュースウィンドウ計算（JST 基準 → UTC 変換）: 前日 15:00 JST ～ 当日 08:30 JST を対象。
  - 銘柄あたりの記事数・文字数上限（トークン爆発対策）。
  - バッチ処理（最大 20 銘柄/チャンク）、JSON Mode を想定したレスポンス検証、スコアクリップ ±1.0。
  - エラー時の指数的バックオフリトライ（429, ネットワーク断, タイムアウト, 5xx）。
  - レスポンスの堅牢なバリデーション（JSON 抽出、results キー検査、型・既知コードの検証）。
  - DuckDB の executemany に関する互換性考慮（空リスト回避）。
  - テスト向けフック: _call_openai_api をモック可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）200日移動平均乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存する score_regime を実装。
  - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
  - マクロキーワードで raw_news をフィルタ、LLM（gpt-4o-mini）で macro_sentiment を算出。
  - 合成スコア = 0.7 * MA 成分 + 0.3 * マクロ成分、閾値で 'bull' / 'neutral' / 'bear' を判定。
  - API 失敗時は macro_sentiment=0.0 でフォールバックするフェイルセーフ。
  - OpenAI 呼び出しはモジュール単位で独立実装（モジュール結合を避ける）。
  - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実装、失敗時は ROLLBACK。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を使用した is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック（休業日は土日扱い）。
    - next/prev の最大探索範囲を設定して無限ループを防止。
    - calendar_update_job: J-Quants API（jquants_client 経由）から差分取得し market_calendar を冪等更新。バックフィル、健全性チェック（将来日付の異常検出）を実装。

  - ETL パイプライン（pipeline）
    - ETLResult dataclass を実装（取得数・保存数・品質問題・エラーを格納）。
    - 差分更新、バックフィル、idempotent 保存（jquants_client の save_* を想定）、品質チェック（quality モジュールと連携）を想定した設計。
    - 内部ユーティリティ: テーブル存在確認、最大日付取得のヘルパーを提供。

  - etl モジュールから ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離
    - Volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比
    - Value: PER（EPS 有効時）・ROE（raw_financials から直近報告を取得）
    - すべて DuckDB SQL を用いて計算（外部 API へのアクセスなし）
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary を実装
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得
    - calc_ic: スピアマンランク相関（ランク化は平均順位 tie を考慮）
    - rank / factor_summary: ランク化と基本統計量計算（外部ライブラリに依存しない実装）
  - research パッケージの __all__ で主要関数を再エクスポート。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 以下の環境変数は本リリースで必須として扱う（設定されていない場合は ValueError を送出する箇所あり）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - OPENAI_API_KEY（AI モジュール呼び出し時。api_key 引数で上書き可能）
- .env 自動ロードはプロジェクトルート検出に依存。公開配布等での運用時は注意。

### 既知の制約 / 注意事項 (Notes)
- ルックアヘッドバイアス対策として datetime.today() / date.today() を参照しない実装方針を採用（target_date 引数ベース）。
- OpenAI 呼び出しのリトライは 429 / ネットワーク断 / タイムアウト / 5xx を対象。その他のエラーは記録してスキップするフェイルセーフ設計。
- DuckDB のバインド互換性のため、executemany に空リストを与えない実装（空時はスキップ）。
- news_nlp と regime_detector はそれぞれ内部で _call_openai_api を独立実装（モジュール間でのプライベート関数共有を避ける）。
- 一部の財務指標（PBR、配当利回りなど）は現バージョンで未実装。
- jquants_client や quality モジュールは参照されているが本変更ログのコード抜粋内では実装を含まない（外部依存）。
- 一部ファイル（例: data.pipeline 内の _adjust_to_trading_day 以降の実装）が抜粋で途中までとなっているため、実際のリリースでは追加実装が存在する想定。

---

今後のリリースでは以下のような改善を想定:
- 統合テスト・ユニットテストの追加（OpenAI モックを利用した回帰テスト）
- パイプライン実行の CLI / スケジューリングラッパー
- 財務指標の拡張（PBR、配当利回り）、およびデータ品質向上のための詳細チェック
- モデル／API 呼び出しの観測性（メトリクス・トレース）の追加

---