# Changelog

すべての重要な変更履歴を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 変更は利用者に影響のある粒度で記載しています（API, 環境変数, 挙動、設計方針など）。
- 初期リリース（0.1.0）として、このリポジトリに含まれる主要機能・モジュールと設計上の重要な挙動をまとめています。

## [0.1.0] - 2026-04-03

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ __all__ に data, strategy, execution, monitoring を設定（外部 API の統一エントリを想定）。

- 環境設定 / config
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して自動検出（カレントワーキングディレクトリに依存しない挙動）。
    - ロード順: OS 環境変数 > .env.local（上書き） > .env（未設定時にセット）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
    - .env のパースは export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などをサポート。
  - Settings クラスで各種設定プロパティを提供:
    - J-Quants / kabu ステーション / LINE / データベースパス（duckdb/sqlite）/監視設定（PID/kill flag/しきい値）/システム設定（env, log_level）など。
    - 環境変数検証（KABUSYS_ENV は development/paper_trading/live、LOG_LEVEL は DEBUG/INFO/... の検証）。
    - Path 型でのパス解決や、bool/float 等の型変換を行うプロパティを用意。

- Data モジュール
  - calendar_management
    - JPX マーケットカレンダー管理（market_calendar）用ユーティリティを実装。
    - 営業日判定関数群を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場面では曜日ベース（土日除外）でフォールバックする制御を実装。
    - 夜間バッチ calendar_update_job: J-Quants API から差分取得 → 冪等保存（ON CONFLICT または同等処理）・バックフィル・健全性チェックを行う。
    - 最大探索日数やバックフィル、lookahead 等の定数で挙動を制御。
  - ETL / pipeline
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。
    - ETL パイプラインの骨格（差分取得、保存、品質チェックフロー）を実装する pipeline モジュールを含む。
    - 差分更新のための最小日付、バックフィル日数、品質チェックの扱い（Fail-Fast にしない設計）などの方針を定義。
    - DuckDB 互換性への考慮（executemany の空リスト回避等）を組み込んだ実装。

- Research モジュール
  - factor_research
    - モメンタム / ボラティリティ / バリュー等の定量ファクター計算関数を提供:
      - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日MA乖離）を計算。データ不足時は None。
      - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。データ不足時は None。
      - calc_value: 最新の raw_financials と当日の株価から PER/ROE を計算。
    - DuckDB のウィンドウ関数を活用し、prices_daily / raw_financials のみを参照する安全な実装。
  - feature_exploration
    - calc_forward_returns: 将来リターン（指定ホライズン）の計算（複数ホライズン一括クエリ、入力バリデーションあり）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。十分な有効レコードがない場合は None を返す。
    - rank: 同順位は平均ランクとするランク化関数（細かい丸めで ties の検出漏れ対策あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - research パッケージ初期公開（主要関数を __all__ で再エクスポート）。

- AI モジュール
  - news_nlp
    - raw_news と news_symbols を使い、OpenAI（gpt-4o-mini）により銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST）および UTC への変換を明確化。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数・文字数上限（デフォルト: 10 件 / 3000 文字）でプロンプト肥大化を抑制。
    - API 呼び出しは冪等性・回復性を重視:
      - 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ。
      - レスポンスの厳密なバリデーション（JSON 抽出、results リスト、code の検証、数値チェック）。
      - スコアは ±1.0 にクリップ。部分失敗時でも他コードの既存スコアを消さないよう、DELETE（対象コードのみ）→ INSERT の置換形式で書き込み。
    - テスト容易性のため OpenAI API 呼び出し箇所を交換可能に設計（_call_openai_api をパッチ可能）。
  - regime_detector
    - ETF 1321（Nikkei 225 連動 ETF）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ書き込む機能を実装。
    - マクロニュース抽出のキーワード集合（日本・米国・グローバル系）によるフィルタリング機能。
    - OpenAI 呼び出しはリトライ/バックオフや API エラー処理を組み込んだ堅牢な実装で、全リトライ消費時やパース失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジーム計算はクリップ処理や閾値に基づいたラベル付けを行い、DB 書き込みは BEGIN / DELETE / INSERT / COMMIT のトランザクションで冪等的に処理。失敗時はROLLBACK を試行。

### Behaviour / Design notes
- ルックアヘッドバイアス対策
  - AI / リサーチの全関数で datetime.today() / date.today() を直接参照せず、明示的な target_date 引数を必須にすることでルックアヘッドを防止する設計。
  - DB クエリでは target_date 未満（排他）や WHERE 範囲制約を用いて将来データの参照を防止。

- DuckDB 互換性への配慮
  - executemany に空リストを渡さないチェック、list 型バインドの互換性回避（個別 DELETE 実行）など、特定 DuckDB バージョンでの制約を考慮した実装。

- トランザクションとフェイルセーフ
  - AI スコア書き込み・レジーム書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で実行。部分失敗時に既存データを不用意に消さない工夫を導入。
  - OpenAI API 呼び出し失敗時は明示的にフォールバック（スコア=0.0 やそのチャンクスキップ）し、例外を上位に波及させない箇所がある（ロバストネス優先）。

### Security / Ops
- OpenAI API キーは api_key 引数か環境変数 OPENAI_API_KEY で解決。未設定時は ValueError を送出する（明示的なエラー）。
- 環境変数の自動ロードはプロジェクトルート検出に基づくため、配布後の実行でも想定通り動作するよう設計。
- 設定に関する敏感情報（例: KABU_API_PASSWORD, JQUANTS_REFRESH_TOKEN）は Settings 経由で必須チェックを行う。

### Compatibility
- 外部依存の最小化: research/feature_exploration は pandas 等に依存せず、標準ライブラリと DuckDB のみで実装。
- OpenAI SDK（openai）の Chat Completions API を利用（gpt-4o-mini をデフォルトモデルに指定）。API レスポンスの将来の変化に備えた堅牢化ロジックを導入。

### Deprecated
- なし（初期リリースのため該当なし）。

### Removed
- なし（初期リリースのため該当なし）。

### Fixed
- なし（初期リリースのため該当なし）。

---

注: 本 CHANGELOG は提供されたコードベースから推測して作成しています。実際のリリースノート作成時は、コミット履歴やリリース担当者の記録を参照して差分・責任者・注釈（既知の制限・未解決の問題など）を追記してください。