# Changelog

すべての変更は「Keep a Changelog」形式に従い、意味のある変更ごとに分類しています。

注: バージョンや日付はコードベースの内容から推測して作成しています（パッケージの __version__ は 0.1.0）。実際のリリース日・バージョン運用に合わせて調整してください。

## [Unreleased]

- （今後の変更をここに記載）

## [0.1.0] - 2026-04-03

初期公開リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主な機能は以下の通りです。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）: バージョン定義とサブパッケージのエクスポート（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env ファイルや環境変数からの設定自動読み込み機能を実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行い、CWD に依存しない実装。
    - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パース機能強化:
    - export KEY=val 形式対応、シングル/ダブルクォートとバックスラッシュエスケープの扱い、インラインコメント処理。
  - 環境変数取得ユーティリティ `Settings` を実装（settings インスタンスをエクスポート）。
    - J-Quants, kabuステーション, LINE, DB パス, 監視関連ファイルパスや閾値、実行環境（development/paper_trading/live）・ログレベルのバリデーション等をプロパティとして提供。
    - 必須項目未設定時は ValueError を送出する `_require`。

- AI モジュール（src/kabusys/ai）
  - ニュース NL P スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約して銘柄ごとにニューステキストを作成し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信してセンチメントを算出。
    - 時間ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）: calc_news_window を提供。
    - バッチ処理（最大 20 銘柄 / チャンク）、1 銘柄あたりの最大記事数・最大文字数によるトリム機能を実装。
    - リトライ戦略: 429、ネットワーク断、タイムアウト、5xx に対する指数バックオフ。最大リトライ回数と待機時間は定数で調整可能。
    - レスポンス検証: JSON 抽出、"results" 配列の検証、未知コードの無視、スコアの数値変換と ±1.0 でクリップ。
    - DB 書き込みは部分原子性を考慮: 成功した銘柄のみを DELETE → INSERT（コード絞り込み）で置換。DuckDB の executemany の挙動に配慮した実装。
    - テストしやすさ: OpenAI 呼び出し（_call_openai_api）を patch で差し替え可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込み銘柄数を返す。API キーが未設定の場合は ValueError。

  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を組み合わせて日次の市場レジーム（bull / neutral / bear）を判定。
    - MA 計算は target_date 未満のデータのみ使用（ルックアヘッド防止）。データ不足時は中立（ma200_ratio=1.0）にフォールバック。
    - マクロニュースはニュース NLP のウィンドウ計算を利用してタイトルを抽出。LLM 呼び出しは独自実装（news_nlp の内部関数を参照しない設計）。
    - LLM 呼び出しに対するリトライ/フォールバック（API エラー時は macro_sentiment=0.0）を実装。
    - スコア合成はクリップ済みで閾値によりラベル化。market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。公開 API: score_regime(conn, target_date, api_key=None)。

- データプラットフォーム / ETL（src/kabusys/data）
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定 API を提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫したロジックを実装。
    - カレンダー夜間バッチ job: calendar_update_job(conn, lookahead_days=...) を実装。J-Quants API から差分取得し保存。バックフィル、健全性チェックを実装。
    - 最大探索日数やバックフィル日数など各種定数を用意して安全性を確保。

  - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETL 実行結果を表す ETLResult dataclass を実装（target_date, fetched/saved カウント、品質チェック結果、エラー等）。
    - 差分更新・保存・品質チェックの処理フローを想定したユーティリティ関数群の骨組み（jquants_client, quality モジュールとの連携を想定）。
    - ETLResult.to_dict() で品質問題をシリアライズ可能。
    - etl モジュールは ETLResult を再エクスポート。

- リサーチ / ファクター（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M 短中長期リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR）、Liquidity（20 日平均売買代金、出来高比率）、Value（PER、ROE）を計算する関数群を提供:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB SQL を用いて効率的に計算。結果は (date, code) を含む dict のリストで返す。
    - データ不足の扱い（必要期間未満は None）を明示。

  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト horizons=[1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col) — Spearman ランク相関（ties 対応）。
    - ランキングユーティリティ: rank(values)（同順位は平均ランク）。
    - ファクター統計サマリ: factor_summary(records, columns) — count/mean/std/min/max/median を算出。
    - 外部依存を避け、標準ライブラリのみで実装（pandas 非依存）。

### 変更
- なし（初期リリースのため該当なし）。

### 修正
- なし（初期リリースのため該当なし）。

### 非推奨
- なし。

### 削除
- なし。

### セキュリティ
- なし。

---

備考（実装上の重要な挙動・設計思想の要約）
- ルックアヘッドバイアス対策: いずれの分析/スコアリング関数も内部で datetime.today() / date.today() を参照せず、引数で与えた target_date に対して厳格に過去データのみを参照する設計。
- フェイルセーフ: 外部 API（OpenAI, J-Quants 等）失敗時は例外を投げずにフォールバック（0.0 / スキップ / 中立）して処理継続する箇所が多く、運用時の堅牢性を重視。
- テスト容易性: OpenAI 呼び出しなどを差し替え可能に実装しており、ユニットテストでのモックが容易。
- DuckDB を主要なストレージ層として利用する想定（SQL クエリは DuckDB 向けに最適化）。

この CHANGELOG はコード内のドキュメント文字列・定数・関数名・コメントから推測して作成しています。実際のリリースノート作成時は、変更履歴やコミットログと合わせて調整してください。