# Changelog

すべての注目すべき変更を Keep a Changelog の形式で記載します。  
このプロジェクトはセマンティック バージョニングに従います。

## [0.1.0] - 2026-04-04

### 追加 (Added)
- パッケージ初期リリース。kabusys の基本モジュール群を提供。
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境変数 / 設定管理モジュールを追加（src/kabusys/config.py）。
  - .env ファイル自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（.env.local は上書きモード）。
  - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサは export 形式, シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
  - 必須設定取得用 _require() と Settings クラスを公開。各種設定プロパティを提供（OpenAI / J-Quants / kabu API / LINE / DB パス / 監視しきい値 / 環境判定 等）。
  - KABUSYS_ENV, LOG_LEVEL の妥当性検証を実装（許容値のチェック）。

- ニュース NLP（AI）モジュール（src/kabusys/ai/news_nlp.py）を追加。
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）でセンチメントを評価して ai_scores テーブルへ書き込み。
  - ニュース対象ウィンドウの計算（JST ベース; 前日 15:00 JST 〜 当日 08:30 JST を UTC に変換）を提供（calc_news_window）。
  - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）でトークン肥大化を抑制。
  - API 呼び出しに対するリトライ（429 / ネットワーク断 / タイムアウト / 5xx）、指数バックオフを実装。
  - レスポンスの厳格なバリデーション（JSON 抽出、"results" リストの検証、code/score の検証、score の ±1.0 クリップ）。
  - 部分失敗時でも既存スコア保護のため、書き込みは対象コードに絞って DELETE → INSERT（トランザクション）を行う（DuckDB の executemany 空リスト制約に対する保護あり）。
  - 公開 API: score_news(conn, target_date, api_key=None) を提供。

- 市場レジーム判定モジュール（src/kabusys/ai/regime_detector.py）を追加。
  - ETF 1321（225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を判定。
  - LLM 評価は gpt-4o-mini（JSON Mode）利用。max リトライ、エラー時は macro_sentiment=0.0 のフォールバック実装。
  - レジームスコア合成、閾値によるラベル付け、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
  - 公開 API: score_regime(conn, target_date, api_key=None)。

- Data モジュール（src/kabusys/data/*）を追加（主に DuckDB を前提とした ETL / カレンダー管理）。
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を利用した営業日判定 API を提供: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB にデータがない場合は曜日ベースでフォールバック（週末: 非営業日）。
    - next/prev_trading_day の探索上限（_MAX_SEARCH_DAYS）を設定し無限ループを防止。
    - 夜間バッチ calendar_update_job: J-Quants クライアント経由で差分取得 → 保存（fetch/save を jquants_client に委譲）、バックフィル・健全性チェック実装。
  - ETL / パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（ETL の実行概要、品質問題・エラーの集約）。
    - 差分更新、バックフィルデフォルト、品質チェック（quality モジュールとの連携）を想定した設計。jquants_client へ差分取得と保存を委任。
    - デフォルト最小データ開始日 (_MIN_DATA_DATE)、カレンダー先読み日数、バックフィル日数を定義。

- Research モジュール（src/kabusys/research/*）を追加。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離 (ma200_dev) を計算（データ不足時は None）。
    - ボラティリティ/流動性: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。
    - バリュー: raw_financials から EPS / ROE を参照して PER / ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB SQL とウィンドウ関数で実装。戻り値は (date, code) ベースの dict リスト。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns: horizons デフォルト [1,5,21]、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic: スピアマンランク相関）、ランク化ユーティリティ rank()。
    - ファクター統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - 研究系ユーティリティ群を __all__ で再エクスポート。

- 研究 / AI / データ処理モジュールで OpenAI クライアント呼び出し箇所を設計上差し替えやすく実装（内部 _call_openai_api をラップ、テスト用に patch 可能）。

### 変更 (Changed)
- なし（初回リリースのため該当なし）。

### 修正 (Fixed)
- なし（初回リリースのため該当なし）。

### 削除 (Removed)
- なし。

### 注意点（設計上の重要挙動）
- ルックアヘッドバイアス防止:
  - AI モジュール / Research / News 集約等は内部で datetime.today() / date.today() を参照せず、外部から渡された target_date を起点に集計ウィンドウを決定します。
  - prices_daily や raw_news へのクエリは target_date 未満 / 半開区間を採用するなど、将来データを参照しない設計。
- フェイルセーフ:
  - OpenAI API の失敗やレスポンスパース失敗は例外を投げずにフォールバック（0.0 スコアやスキップ）して処理を継続する方針。
  - ETL の品質チェックは致命的エラーでも全件検査を行い、呼び出し側で対応を決められるようにしています。
- DuckDB の executemany に関する互換性対応（空リスト送信不可）を考慮した実装（空チェックを行ってから executemany を呼ぶ）。
- .env パースの細かい挙動（クォート内のエスケープ処理、コメント判定ルール）に依存するため .env 作成時は .env.example に従うこと。

### 既知の制約 / 将来の改善余地
- OpenAI モデル名がハードコード（gpt-4o-mini）。将来的にモデル差し替えを容易にする設定化の余地あり。
- jquants_client / quality モジュールは本実装では外部依存のインターフェースとして利用しており、実行環境に応じたクライアント実装が必要。
- News / Regime の LLM プロンプトや JSON Mode のフォールト処理は実運用で追加チューニングが必要になる可能性あり。
- 一部の SQL は DuckDB のバージョン差に影響される可能性がある（配列バインド等）。

---

開発・運用チーム向け: 追加された公開関数・クラス（主なもの）
- settings (kabusys.config.Settings) と個別プロパティ
- score_news(conn, target_date, api_key=None)
- score_regime(conn, target_date, api_key=None)
- calc_news_window(target_date)
- calendar management: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- ETLResult (kabusys.data.pipeline.ETLResult)
- research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

以上。