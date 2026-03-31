# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog のガイドラインに準拠しています。  

## [Unreleased]

### 注意事項
- 現在のスナップショットは機能実装を中心とした初期リリース相当の内容です。将来的な改善点（例：OpenAI呼び出しの抽象化、より詳細なテストカバレッジ、エラーハンドリングの細分化など）を計画しています。

---

## [0.1.0] - 2026-03-31

初回公開リリース。以下の主要機能とユーティリティを実装しました。

### 追加された機能
- パッケージ基盤
  - パッケージ名: kabusys
  - パッケージバージョン: 0.1.0
  - APIエントリポイントのエクスポート: data, strategy, execution, monitoring（__all__ により公開）

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数の自動読み込み機能を実装
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env / .env.local を読み込む
    - OS 環境変数を保護する仕組み（protected set）を採用し、.env.local で上書き可能
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）
  - .env パーサーの実装（export 文、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）
  - Settings クラスを実装し、アプリケーション設定をプロパティで提供
    - J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル等
    - 値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須キーの必須チェック(_require)

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI (gpt-4o-mini) を用いたセンチメント評価を実施
    - タイムウィンドウ計算（JST基準 → UTC変換）を実装（calc_news_window）
    - バッチ処理（1回につき最大 20 銘柄）、1銘柄あたり記事数・文字数の上限指定（トリム）
    - OpenAI JSON mode を利用した応答処理、レスポンスのバリデーション（results リスト、code/score）、スコアを ±1.0 にクリップ
    - リトライ戦略：429・ネットワーク断・タイムアウト・5xx に対する指数バックオフ
    - DB への冪等書き込み（DELETE → INSERT）を実装（部分失敗時に既存スコアを保護）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム判定
    - MA 計算（ルックアヘッド防止のため target_date 未満データのみ使用）
    - マクロニュース抽出（マクロキーワードに基づくタイトル抽出、最大記事数制限）
    - OpenAI 呼び出し（gpt-4o-mini）で JSON 形式の macro_sentiment を取得、リトライ・フォールバック処理を実装（API失敗時は 0.0）
    - レジームスコア合成とラベリング（bull / neutral / bear）
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時 ROLLBACK 処理）

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar を用いた営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動
    - カレンダー夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック）
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを実装（target_date, fetched/saved カウント、quality issues, errors）
    - 差分更新・保存・品質チェックの方針に沿ったユーティリティを実装（ETL 基盤）
    - データベーステーブル存在チェック等のユーティリティ関数を実装
  - ETL の公開インターフェース（etl）として ETLResult を再エクスポート

- 研究/リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日 MA 乖離率）
    - Volatility / Liquidity: 20日 ATR（atr_20）, 相対 ATR (atr_pct), 20日平均売買代金(avg_turnover), volume_ratio
    - Value: PER（price / EPS, EPS が 0/欠損時は None）, ROE（raw_financials から取得）
    - DuckDB SQL を活用した高性能実装、結果は (date, code) をキーとする dict のリストで返却
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、入力検証あり
    - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関、None/不足データ対応
    - ランク関数（rank）: 同順位は平均ランクで処理、丸めで ties の扱いを安定化
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None を除外）

### 変更・改善
- OpenAI 呼び出しに対する堅牢性向上
  - JSON 形式パースの堅牢化（前後余計テキストが混ざる場合の {} 抽出、パース失敗時のフォールバック）
  - API エラーの種別ごとにリトライ戦略を分離
- DuckDB に対する互換性考慮
  - executemany の空リストバインドに関する回避（DuckDB 0.10 に対応）
  - date 型の取り扱いを一貫させるユーティリティ関数を導入

### 修正された問題
- （初期実装における）LLM レスポンスの不正フォーマットや API 一時障害を想定したフォールバックを導入。これにより API 失敗時に処理を中断せず継続できるようにした。

### 既知の制約・注意点
- OpenAI API キーは必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
- DuckDB のバージョン依存の挙動（特に executemany の挙動）に注意。コードは互換性を考慮してあるが、運用時に利用している DuckDB バージョンでの確認が推奨されます。
- news_nlp/regime_detector は外部 API（OpenAI）に依存するため、API 利用料金やレート制限に注意してください。
- calendar_update_job は J-Quants クライアント（kabusys.data.jquants_client）に依存します。API 例外時は安全に失敗してログを残す設計です。
- 現時点の実装はユニットテストのフック（_call_openai_api の差し替え）を用意していますが、実際の E2E テストやモックの整備が必要です。

---

（注）本 CHANGELOG はコードベースの内容から推測して作成した初期リリース記録です。実際のコミット履歴やリリースノートが存在する場合はそちらを優先してください。