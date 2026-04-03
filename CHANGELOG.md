# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠します。

リリース日表記はコミット時点の想定日です（推測に基づく）。

## [0.1.0] - 2026-04-03

初期リリース。本バージョンで導入された主要機能・修正点を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。バージョンは 0.1.0。
  - public API エクスポート: data, strategy, execution, monitoring モジュールを __all__ で公開。

- 環境設定・ロード機能
  - 環境変数/設定管理モジュールを実装（kabusys.config.Settings）。
  - .env / .env.local ファイルの自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いに対応。
  - .env ロード時に既存 OS 環境変数を保護する protected キーセットを導入。
  - Settings に各種プロパティを提供（J-Quants トークン、kabu API 設定、LINE トークン、DB パス、監視関連閾値、実行環境判定、ログレベル検証等）。不正値は ValueError で通知。

- AI（NLP）機能
  - ニュースセンチメント分析モジュールを実装（kabusys.ai.news_nlp.score_news）。
    - 指定の時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）に基づく記事収集（calc_news_window）。
    - raw_news と news_symbols を結合して銘柄単位に記事を集約（記事件数・文字数上限でトリム）。
    - 最大 20 銘柄を 1 チャンクとして OpenAI（gpt-4o-mini）へバッチ送信。
    - JSON Mode 応答のバリデーションとスコア抽出（結果は ±1.0 にクリップ）。
    - API 呼び出しに対するリトライ（429、ネットワーク断、タイムアウト、5xx に対して指数バックオフ）。
    - 部分失敗を考慮した idempotent な DB 書き込み（DELETE → INSERT、書込み対象コードのみ置換）と DuckDB executemany の空パラメータ対策。
    - テスト用に _call_openai_api を分離して差し替え可能に実装。

  - 市場レジーム判定モジュールを実装（kabusys.ai.regime_detector.score_regime）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースフィルタリング（マクロキーワード群）→ OpenAI による JSON 出力パース。
    - API 障害時は macro_sentiment=0.0 のフェイルセーフ、リトライ・バックオフを実装。
    - 計算結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時に ROLLBACK）。

- リサーチ（ファクター）機能
  - ファクター計算モジュールを実装（kabusys.research.factor_research）。
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算。真の true_range の扱いを明確化（high/low/prev_close に NULL があれば true_range を NULL に）。
    - calc_value: raw_financials から最新財務を取得し PER（EPS の 0/欠損は None）・ROE を計算。
    - すべて DuckDB 接続を受け取り prices_daily/raw_financials のみ参照（副作用なし）。
  - 特徴量探索モジュールを実装（kabusys.research.feature_exploration）。
    - calc_forward_returns: 指定ホライズンの将来リターンをまとめて取得（可変 horizons、入力検証あり）。
    - calc_ic: スピアマンランク相関（IC）を実装（欠損・同値の扱いに配慮）。
    - rank: 同順位を平均ランクで扱う安定実装（round による丸めで ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

  - research パッケージの __init__ で主な関数群と zscore_normalize（kabusys.data.stats から）を再エクスポート。

- データ基盤（Data Platform）
  - カレンダー管理モジュールを実装（kabusys.data.calendar_management）。
    - market_calendar を使った営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値を優先し、未登録日は曜日ベース（平日）でフォールバックする一貫したロジック。
    - 夜間バッチ更新 job（calendar_update_job）を実装: J-Quants API から差分取得、バックフィル（直近 N 日）および健全性チェックを行い idempotent に保存。
  - ETL パイプライン基盤を実装（kabusys.data.pipeline）。
    - ETLResult dataclass を定義（取得数、保存数、品質問題、エラー一覧等を保持）。
    - 差分更新、バックフィル、品質チェックのためのユーティリティを提供。
  - data.etl を通じて ETLResult を再エクスポート。

### 変更 (Changed)
- 設計方針・安全対策の明確化
  - 多くの分析/スコアリング関数でルックアヘッドバイアスを避けるために datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計に統一。
  - OpenAI 呼び出しや DB 書き込み周りをフェイルセーフに：API 失敗時に処理継続（スコアは 0.0 またはスキップ）、DB 書き込みはトランザクションで保護。
  - DuckDB のバージョン差異に配慮した実装（executemany の空リスト問題への対応、list バインドの回避など）。
  - テストのしやすさを考慮し、外部 API 呼び出し箇所を関数として分離（unit test で patch 可能）。

### 修正 (Fixed)
- ロバストネス向上
  - .env 読み込みでの I/O エラー時に警告を出力して処理を継続（致命的失敗を回避）。
  - OpenAI レスポンスの JSON パース失敗や予期しない形式に対して警告ログを出し、安全側のデフォルトを使用。
  - market_regime / ai_scores 書き込み処理で例外発生時に ROLLBACK を試み、さらに ROLLBACK 自体の失敗もログ出力。

### 内部（Internal）
- OpenAI API 用のモデル指定やバックオフパラメータ、バッチサイズ等の定数をモジュール内定数として整理。
- 各モジュールで詳細なログメッセージを追加（debug/info/warning/exception を活用）。

---

今後の予定（想定）
- strategy / execution / monitoring の実装拡充（現時点ではパッケージ構成にプレースホルダあり）。
- テストカバレッジ拡大、CI 上での DuckDB テストデータ整備、OpenAI 呼び出しのモック強化。
- J-Quants / kabu API クライアントの統合的なエラーハンドリング・リトライ設定の追加。

（注）本 CHANGELOG は提供されたコードからの推測に基づき作成しています。実際のリリースノートではコミット履歴・設計文書・リリース日を参照のうえ適宜修正してください。