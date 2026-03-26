CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
主な変更点はコードベースから推測して記載しています（初回リリース相当のまとめ）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-26

初回公開リリース。以下の主要機能と実装方針を含みます。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - モジュール分割：data, research, ai, monitoring, strategy, execution 等の名前空間を想定（__all__ に記載）。

- 設定・環境管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml）に基づく自動 .env 読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env の堅牢なパーサ（export prefix、クォート文字内のエスケープ、インラインコメントの扱いなどに対応）。
  - 環境変数の必須チェック（_require）とバリデーション（KABUSYS_ENV, LOG_LEVEL）。
  - DuckDB / SQLite のデフォルトパス設定、Slack / API トークン取得プロパティなど。

- AI（kabusys.ai）
  - ニュースセンチメント（score_news）
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチ解析して銘柄ごとのスコアを ai_scores テーブルへ書き込む。
    - 一銘柄あたりの上限記事数・文字数トリム、チャンク処理（デフォルト 20 銘柄/チャンク）、JSON レスポンス検証、スコアのクリップ（±1.0）。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフでのリトライ。API 失敗時は該当チャンクをスキップ（フェイルセーフ）。
    - DuckDB への冪等置換（DELETE → INSERT）を実施し、部分失敗時に既存データを保護。

  - 市場レジーム判定（score_regime）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の market_regime を計算・書き込み。
    - ニュース抽出はマクロキーワードでフィルタし、OpenAI に JSON 出力を要求。API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レジーム判定結果は -1..1 をクリップし閾値で bull/neutral/bear ラベリング。DuckDB への冪等書き込みを行う（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

  - OpenAI 呼び出しはテストで差し替え可能なポイント（_call_openai_api）を用意。

- データ処理・ETL（kabusys.data）
  - ETL 結果を表す ETLResult データクラス（pipeline.ETLResult）を公開（data.etl で再エクスポート）。
  - pipeline モジュール：差分取得、backfill、品質チェック（quality モジュール連携）を想定した ETL 基盤のユーティリティ関数群（テーブル存在確認、最大日付取得など）。
  - calendar_management モジュール：
    - JPX カレンダー（market_calendar）を扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - カレンダー未取得時の曜日ベースフォールバック、DB 登録値優先の一貫した判定ロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新。バックフィル・健全性チェック（将来日チェック）を実装。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離などを DuckDB SQL ベースで計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率などを計算。true_range の NULL 伝播などデータ品質に配慮。
    - calc_value: raw_financials と prices_daily を組合せて PER/ROE を計算（EPS が 0 または欠損なら None）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンに対する将来リターン計算（デフォルト [1,5,21]）、ホライズンのバリデーション。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算。サンプル数不足時は None。
    - rank: 同順位は平均ランクとするランクセーブ関数（浮動小数の丸め対策あり）。
    - factor_summary: count/mean/std/min/max/median の統計要約を標準ライブラリのみで提供。

- 実装方針・運用配慮（横断的）
  - DuckDB を主要なローカル分析 DB として利用（埋め込み SQL を多用）。
  - 全ての処理でルックアヘッドバイアス回避を明示（datetime.today()/date.today() を直接参照しない設計、ターゲット日を引数で与える）。
  - OpenAI 呼び出しや DB 書き込み箇所はフェイルセーフ設計（API 失敗はフォールバック or スキップ、DB 書き込みはトランザクション／ロールバック処理）。
  - テスト容易性のため API 呼び出し箇所に差し替えポイントを用意（unittest.mock.patch などで差し替え可能）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

---

備考:
- ここに記載した機能説明・設計方針はコードベースの実装から推測したものであり、ユーザードキュメントやリポジトリの README に記載の内容を補完する目的でまとめています。