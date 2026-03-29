# CHANGELOG

すべての変更は Keep a Changelog の規約に従って記載しています。  
互換性のあるバージョニングは SemVer を使用します。

## [0.1.0] - 2026-03-29

初回公開リリース。日本株のデータ取得・ETL・研究用ファクター計算、ニュース NLP、ならびに市場レジーム判定を含む基本ライブラリを提供します。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名 kabusys を追加。公開 API として data / strategy / execution / monitoring モジュールを想定している（__all__ にてエクスポート）。
  - バージョン情報を `__version__ = "0.1.0"` として設定。

- 環境設定 / 初期化 (`kabusys.config`)
  - .env ファイル（`.env` / `.env.local`）と OS 環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能（テスト向け）。
    - プロジェクトルート判定は `pyproject.toml` または `.git` を基準に行い、CWD に依存しない動作に設計。
  - `.env` パーサを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
  - 必須環境変数取得ヘルパー `_require` と Settings クラスを提供。
    - 必須項目例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - `KABUSYS_ENV`（development / paper_trading / live）や `LOG_LEVEL` の検証ロジックを実装。

- データ関連 (`kabusys.data`)
  - ETL パイプライン (`kabusys.data.pipeline`)
    - 差分更新、バックフィル、品質チェック統合を想定した ETLResult データクラスを実装。
    - DuckDB を想定した最大日付取得・テーブル存在チェック等のユーティリティ。
    - ETL 実行結果を辞書化する `to_dict` を提供（品質問題は (check_name, severity, message) 形式で出力）。
  - ETL インターフェース再エクスポート (`kabusys.data.etl`)。
  - マーケットカレンダー管理 (`kabusys.data.calendar_management`)
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job` を実装（J-Quants クライアントを利用）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を提供。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - 最大探索範囲・バックフィル・健全性チェックなど安全機構を搭載。

- 研究用モジュール (`kabusys.research`)
  - ファクター計算 (`kabusys.research.factor_research`)
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0 / NULL の場合は None）、ROE（raw_financials からの取得）。
    - DuckDB による SQL ベースの集計実装。データ不足時は None を返す仕様。
  - 特徴量探索 (`kabusys.research.feature_exploration`)
    - 将来リターン計算: 複数ホライズン（デフォルト [1,5,21]）に対応する `calc_forward_returns`。
    - IC（Information Coefficient）計算: スピアマンランク相関で `calc_ic` を実装（有効データが 3 件未満の場合は None）。
    - ランク関数 `rank`（同順位は平均ランク、丸めによる ties 対策あり）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
  - 研究用補助関数群をパッケージレベルで再エクスポート。

- AI / ニュース NLP (`kabusys.ai`)
  - ニュース NLP スコアリング (`kabusys.ai.news_nlp`)
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出、`ai_scores` テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換したウィンドウを使用）。窓の算出は `calc_news_window`。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1 銘柄あたりの最大記事数・最大文字数によるトークン肥大化対策（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - 再試行/バックオフ戦略（429/ネットワーク/タイムアウト/5xx をリトライ）、レスポンス検証とスコアクリップ（±1.0）。
    - 部分失敗に備え、書き込みは該当コードのみ DELETE → INSERT の置換を行い既存データ保護。
    - テスト容易性: OpenAI 呼び出し部分はモック差し替え（unittest.mock.patch）を想定。
  - 市場レジーム判定 (`kabusys.ai.regime_detector`)
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定し `market_regime` テーブルに冪等書き込みを行う。
    - MA200 比率は過去データのみを参照（ルックアヘッド防止）。ニュースは `news_nlp.calc_news_window` を利用して同様の時間窓を抽出。
    - OpenAI 呼び出しは専用の内部実装、リトライ・指数バックオフ、API 失敗時は macro_sentiment=0.0 のフォールバック（フェイルセーフ）。
    - 出力はレジームスコア（-1〜1）を計算し閾値でラベル付け。書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等実装。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 既知の注意点 / 実装上のポイント
- OpenAI API の利用には環境変数 `OPENAI_API_KEY` または各関数に明示的な `api_key` 引数の指定が必要。未設定時は ValueError を送出する設計。
- 各 AI モジュールは API 失敗時に例外を投げずにフォールバック（スコア 0 もしくはスキップ）して継続する実装方針。呼び出し側で異常扱いにするかどうかを判断できるようにしている。
- DuckDB のバージョン差異（executemany の空リスト扱いなど）を考慮した実装（空リストでの executemany 実行を避ける等）。
- 時刻扱いは timezone-naive な UTC 想定（DB 側には UTC で保存されている前提）。全ての関数は datetime.today()/date.today() を直接参照しない設計でルックアヘッドバイアスを回避。
- .env パーサは多くのケースをカバーするが、非常に複雑なシェル式の評価は行わない（シンプルな key=value 形式を想定）。
- calendar_update_job / ETL 周りは外部 J-Quants クライアント（kabusys.data.jquants_client）の存在を前提としている。実行時にクライアント実装と接続情報が必要。

---

今後の予定:
- strategy / execution / monitoring の具体的な実装とドキュメントを追加予定。
- テストカバレッジ拡張（ユニット・統合テスト）、および CI/CD の整備。
- モデル運用面の改善（モデル切替、料金最適化、ローカル代替モデルのサポート）。

もしこの CHANGELOG に不足・誤りがあれば指摘してください。