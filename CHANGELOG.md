# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
https://keepachangelog.com/ja/

なお、本リポジトリの初期リリースはバージョン 0.1.0 として記録しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-04
初回公開リリース。

### 追加
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に定義

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を起点）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装（コメント・export プレフィックス・クォート・エスケープ対応）
  - 環境変数取得ヘルパ: _require と Settings クラスを提供
  - 設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_*、データベースパス、監視設定、しきい値、環境・ログレベル判定など）
  - Settings に env 検証（development/paper_trading/live）とログレベル検証を実装

- AI モジュール (src/kabusys/ai/)
  - ニュース NLP (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出し ai_scores テーブルへ書き込み
    - 時間ウィンドウ計算（JST 基準を UTC に変換する calc_news_window を実装）
    - 1チャンクあたり最大 20 銘柄、1 銘柄当たり最大 10 記事、3000 文字でトリムする対策
    - JSON Mode の使用（厳密な JSON を期待）、レスポンスのバリデーション、スコア ±1.0 にクリップ
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）用の指数バックオフ実装
    - 部分失敗に備え、書き込み時は対象コードのみ DELETE → INSERT（冪等・部分保護）
    - テスト容易性のため _call_openai_api を差し替え可能に設計
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（N225 連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定
    - ma200_ratio 計算（target_date 未満のデータのみ使用してルックアヘッドを防止）
    - マクロキーワードで raw_news をフィルタしてタイトルを取得（最大 20 件）
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価（JSON パース、フォールバック時 macro_sentiment=0.0）
    - スコア合成・閾値判定（クリップ・閾値定義）と market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）
    - API 再試行・サーバーエラー取り扱い、テスト差し替えを想定した設計
    - 設計方針として内部で datetime.today()/date.today() を参照せず、引数 target_date を基準にしたルックアヘッドバイアス対策を実施

- Data（データ基盤）モジュール (src/kabusys/data/)
  - カレンダー管理 (src/kabusys/data/calendar_management.py)
    - JPX カレンダー管理 API と連携する夜間バッチ calendar_update_job を実装（J-Quants client を参照）
    - market_calendar テーブルの最終日チェック・差分取得・オンコンフリクト保存（冪等）
    - 営業日判定とユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがない場合や NULL が存在する場合は曜日ベースのフォールバック（週末判定）を一貫して利用
    - 最大探索日数・バックフィル・健全性チェック等の安全処理を実装
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL の取得数・保存数・品質問題・エラーを集約）
    - 差分更新、バックフィル、品質チェック連携、id_token 注入などを設計方針として説明（実処理の土台を提供）
    - _table_exists、_get_max_date 等の内部ユーティリティを追加

- Research（リサーチ）モジュール (src/kabusys/research/)
  - factor_research (src/kabusys/research/factor_research.py)
    - Momentum / Value / Volatility / Liquidity の定量ファクター計算を実装
    - calc_momentum: 1M/3M/6M リターン・200 日 MA 乖離を計算（データ不足時は None）
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を計算
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS が 0/欠損時は None）
    - DuckDB を用いた SQL ベース処理で、prices_daily / raw_financials のみ参照（安全な分離）
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）に対する将来リターンを一括クエリで取得
    - calc_ic: スピアマン（ランク）相関（IC）計算を実装（3 レコード未満は None）
    - rank: 同順位に平均ランクを与える安定したランク化を実装（丸め処理で ties に強い）
    - factor_summary: count/mean/std/min/max/median の統計サマリーを実装（None を除外）
  - research パッケージ __init__ に主要関数を再公開

### 変更（設計上の注意）
- AI 呼び出しは API キーを関数引数で注入可能（テスト容易性）で、未設定時は環境変数 OPENAI_API_KEY を参照して ValueError を発生させる挙動を統一
- LLM 結果のパース失敗や API 障害は例外をそのまま上げず、フェイルセーフで 0.0 を返す、または該当処理をスキップすることでパイプライン全体の継続性を確保
- DuckDB への書込みは冪等性を重視（DELETE → INSERT のパターン、BEGIN/COMMIT/ROLLBACK 対応）
- ルックアヘッドバイアス防止のため、日付処理は外部から与えられる target_date に依存する設計

### 修正（バグ修正）
- （初版のため過去差分なし。実装中に見つかった想定バグ対応をコード内で考慮）
  - JSON mode の不確実性に対する後処理（最外の {} 抽出）でパース耐性を向上
  - DuckDB executemany の空リスト制約への対応（空リストチェックを追加）

### 既知の制限 / 注意事項
- OpenAI クライアントは gpt-4o-mini を前提にしているが、SDK の将来の変更（例: APIError の属性）への柔軟性は一部確保しているものの、環境により追加対応が必要な場合あり
- news_nlp と regime_detector はそれぞれ独自に _call_openai_api を持ち、意図的に共通化していない（モジュール結合を避けるため）
- 一部の外部依存（J-Quants クライアントや J-Quants API レスポンス形式、DuckDB のバージョン差）により実運用時に微調整が必要

### セキュリティ
- 環境変数やトークンの管理は Settings で扱う設計。トークンのログ出力は行わないことを想定（実装でも明示的なログ出力はなし）。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 向け）

---

開発・利用に関する詳細設計や API 仕様（DataPlatform.md / StrategyModel.md 等）はソース内ドキュメンテーションを参照してください。追加の変更履歴はリリースごとに追記します。