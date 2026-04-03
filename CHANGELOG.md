# CHANGELOG

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
初回リリース (0.1.0) に含まれる機能と設計上の注意点を日本語でまとめています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03
初回リリース。

### Added
- パッケージの基礎構成
  - パッケージメタ情報: kabusys v0.1.0（src/kabusys/__init__.py）
  - 公開サブモジュール: data, research, ai, config, などの骨組みを提供。

- 環境変数 / 設定管理 (src/kabusys/config.py)
  - .env ファイルと OS 環境変数の自動ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。
  - auto load を無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パースの堅牢化:
    - export KEY=val 形式対応
    - シングル／ダブル引用符内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート無しは直前に空白/タブがある `#` をコメントとみなす）
  - Settings クラスを提供し、アプリケーションで必要な設定値（J-Quants, kabuステーション, LINE, データベースパス, 監視閾値, 実行環境 等）をプロパティ経由で取得可能。
  - 必須値取得ヘルパー `_require` により未設定時は明確な ValueError を送出。
  - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。

- データ層（DuckDB）ユーティリティ・ETL（src/kabusys/data/…）
  - calendar_management:
    - JPX マーケットカレンダー管理、営業日判定・前後営業日の取得、期間内営業日列挙、SQ日判定ロジックを実装。
    - DB にデータがない場合は曜日ベース（土日を除く）でフォールバックする一貫した挙動。
    - calendar_update_job により J-Quants から差分取得して冪等的に保存。バックフィル、健全性チェックを実装。
  - pipeline / etl:
    - ETLResult データクラスを導入（ETL 結果、品質問題リスト、エラーメッセージ等を保持）。
    - 差分更新、バックフィル方針、品質チェックの連携を想定した基盤を実装。
    - DuckDB の互換性に配慮した実装（executemany に空リストを渡さない等）。
  - jquants_client と連携する想定で、idempotent な保存（ON CONFLICT 相当）を前提とした設計。

- AI / NLP（OpenAI 統合） (src/kabusys/ai/…)
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini の JSON mode）でセンチメントを算出して ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トークン肥大化対策（最大記事数・最大文字数トリム）を実装。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）と指数バックオフ、レスポンスの厳密なバリデーション（JSON 抽出、results 配列/型/コード照合/スコア数値検証）を実装。
    - API 失敗やパース失敗時は該当チャンクをスキップし、他の銘柄のスコアは保護する（部分失敗耐性）。
    - テスト容易性のため OpenAI 呼び出し部分は専用の private 関数に分離しており、ユニットテストで差し替え可能。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini JSON mode）でマクロセンチメントを取得。API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - DB クエリはルックアヘッドバイアス回避のため target_date 未満のデータのみを使用する設計。
    - OpenAI 呼び出し関数は news_nlp とは別実装でモジュール結合を避ける。

- リサーチ / ファクター（src/kabusys/research/…）
  - factor_research:
    - Momentum: 1M/3M/6M リターン, 200 日移動平均乖離（ma200_dev）の計算。
    - Volatility & Liquidity: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - Value: raw_financials からの EPS/ROE を用いた PER、ROE の計算（target_date 以前の最新財務データを使用）。
    - SQL を活用した高速処理、データ不足時は None を返す安全な挙動。
  - feature_exploration:
    - 将来リターン calc_forward_returns（複数 horizon を同時取得する最適化クエリ）。
    - calc_ic（Spearman ランク相関）、rank（同順位は平均ランクで処理）および factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等の外部依存を持たない純標準ライブラリ + DuckDB 実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- （初回リリースのため該当なし）

## 重要な設計上の注意点 / マイグレーションガイド
- OpenAI API
  - API キーは api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照します。未設定の場合は ValueError を送出します。
  - 使用モデルは gpt-4o-mini、JSON mode を利用する前提です。レスポンスパースに失敗した場合は安全側のフォールバック（0.0 やスキップ）を行います。
  - ユニットテストでは各モジュールの private な _call_openai_api をモックしてテスト可能です。

- 環境変数 / .env の扱い
  - 自動ロードはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に行います。プロジェクトルートが見つからない場合は自動ロードをスキップします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - 重要な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - OPENAI_API_KEY（AI 機能使用時に必須）
    - その他（KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH 等）を Settings 経由で利用可能。

- DuckDB 互換性
  - executemany に空リストを渡せないバージョン（例: DuckDB 0.10）への互換性を考慮し、空チェックを行ってから executemany を呼び出します。

- ルックアヘッドバイアス対策
  - 主要なスコア算出関数（score_news, score_regime, ファクター計算等）は内部で datetime.today() / date.today() を参照せず、引数の target_date に基づいて deterministic に動作します（一部バッチジョブ calendar_update_job は date.today() を利用）。

- トランザクションと冪等性
  - market_regime / ai_scores 等への書き込みは、BEGIN / DELETE / INSERT / COMMIT のパターンで冪等書き込みを行い、例外時は ROLLBACK を試みます。ROLLBACK に失敗した場合は警告ログを出します。

## 開発者向けメモ
- テストしやすさのため、外部 API 呼び出し箇所は内部関数で分離（_call_openai_api 等）。ユニットテストではこれらをパッチして API をシミュレートしてください。
- ロギングを各モジュールに組み込んでいるため、デバッグ時は LOG_LEVEL を DEBUG に設定すると詳細な実行情報が得られます。

---

作成した CHANGELOG はコードベース（v0.1.0）の主要機能と設計上の重要ポイントを反映しています。追加でリリースノートの簡潔化や英語版の併記が必要であれば教えてください。