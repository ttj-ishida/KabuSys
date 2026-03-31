# Changelog

すべての注目すべき変更点を記述します。  
このファイルは Keep a Changelog の形式に準拠しています。バージョン番号を基準に差分を管理してください。

※日付はコードベースの最終確認日（この CHANGELOG 作成日）を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-31
初回リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: `kabusys`、初期バージョン `0.1.0` を定義。
  - 公開モジュール: `data`, `strategy`, `execution`, `monitoring` を __all__ に設定。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定を自動読み込みするユーティリティを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動的に .env/.env.local を読み込む。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動読み込みを無効化可能。
    - `.env` のパースは export プレフィックス、クォート内のエスケープ、インラインコメント等に対応。
    - 読み込み時の上書き制御（override）と、OS 環境変数を保護する protected セットをサポート。
  - `Settings` クラスでアプリケーション設定をプロパティとして公開（J-Quants, kabuAPI, Slack, DB パス, 監視閾値 等）。
    - 必須環境変数の未設定時は ValueError を送出する `_require` を利用。
    - `KABUSYS_ENV` と `LOG_LEVEL` の値バリデーションを実装（許容値チェック）。
    - パス系設定は `Path.expanduser()` を利用してユーザーフレンドリに対応。

- AI モジュール (`kabusys.ai`)
  - ニュース NLP (`news_nlp.py`)
    - raw_news / news_symbols を集約して銘柄ごとのニューステキストを作成。
    - OpenAI（gpt-4o-mini、JSON mode）を用いたバッチセンチメント評価を実装（バッチサイズ、トークン肥大対策あり）。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）を指数バックオフで実施。
    - レスポンスの厳密バリデーションと復元ロジック（前後余分テキストから最外の {} を抽出）。
    - スコアを ±1.0 でクリップし、取得したスコアを ai_scores テーブルへ冪等的に書き込む（DELETE → INSERT、部分失敗時の保護）。
    - テスト容易性のため、OpenAI 呼び出し関数を容易に差し替えられる設計。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を提供する `calc_news_window` を実装。
  - 市場レジーム判定 (`regime_detector.py`)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）を実装。
    - prices_daily からの MA 計算、raw_news からのマクロ記事抽出、OpenAI による JSON 出力の解析、スコア合成、market_regime テーブルへの冪等書き込みを網羅。
    - API の多重失敗時は macro_sentiment を 0.0 にフォールバックするフェイルセーフ設計。
    - OpenAI API 呼び出し部分は別モジュールと共有しない独立実装（モジュール結合を低減）。
    - テスト用に API 呼び出し関数を差し替え可能。

- データプラットフォーム (`kabusys.data`)
  - カレンダー管理 (`calendar_management.py`)
    - JPX カレンダーの夜間差分更新ジョブ `calendar_update_job` を実装（J-Quants API 経由、バックフィル、健全性チェック、冪等保存を含む）。
    - 営業日判定ユーティリティ: `is_trading_day`, `next_trading_day`, `prev_trading_day`, `get_trading_days`, `is_sq_day` を実装。DB 登録値優先、未登録日は曜日ベースでフォールバック。
    - 最大探索日数制限による無限ループ防止、NULL 値検出時の警告ログ出力等の堅牢化。
  - ETL パイプライン (`pipeline.py`)
    - 差分取得・保存・品質チェックを行う ETL の骨組みを実装。
    - ETL 実行結果を表現する `ETLResult` dataclass（品質問題一覧・エラー一覧・取得/保存件数 等）を実装し、辞書化メソッド `to_dict` を提供。
    - jquants_client と quality モジュールを前提とした差分取得・保存の方針をドキュメント化。
    - DuckDB の互換性に配慮したテーブル存在チェックなどのユーティリティを実装。
  - ETL 公開インターフェースとして `etl.py` で `ETLResult` を再エクスポート。

- リサーチ（因子・特徴量解析） (`kabusys.research`)
  - ファクター計算 (`factor_research.py`)
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離を計算する `calc_momentum` を実装（DuckDB SQL による高速集計）。
    - Volatility/Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算する `calc_volatility` を実装。true_range の NULL 伝播を意識した実装。
    - Value: raw_financials と prices_daily を組み合わせて PER/ROE を計算する `calc_value` を実装。
    - いずれもデータ不足時は None を返す設計（堅牢性確保）。
  - 特徴量探索 (`feature_exploration.py`)
    - 将来リターン計算 `calc_forward_returns`（可変ホライズン対応、入力検証あり）。
    - IC（Spearman ランク相関）を計算する `calc_ic`（欠損・固定値対応、十分なサンプル数チェックあり）。
    - 値をランクに変換する `rank` ユーティリティ（タイ同順位は平均ランク）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）を実装。
    - すべて外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。

- テスト・運用を考慮した設計
  - 外部 API 呼び出し（OpenAI など）は API キー引数を受け取り、環境変数にフォールバックする形でテスト時にキー注入・モック差し替えが可能。
  - 日付処理では内部で datetime.today()/date.today() を直接参照せず、外部からの target_date を必須にすることでルックアヘッドバイアスを抑止。
  - DB 書き込みは明示的なトランザクション（BEGIN / DELETE / INSERT / COMMIT）を使用し、失敗時は ROLLBACK を試行してログ出力する。

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 削除 (Removed)
- なし（初回リリース）

### セキュリティ (Security)
- なし（初回リリース）

---

開発メモ / 注意点:
- DuckDB のバージョン差異に対する互換性考慮（executemany の空リスト制約、配列バインドの安定性）をいくつかの実装で反映しています。運用環境の DuckDB バージョンに応じた追加確認を推奨します。
- OpenAI 呼び出し部分は API の SDK 変更に対し保守の必要があります（status_code の存在有無への対応等を実装済み）。
- .env パーサは POSIX 系の .env 構文を想定し、クォート内のエスケープ処理やインラインコメントの扱いを実装していますが、特殊ケースがあれば実運用での追加テストを推奨します。