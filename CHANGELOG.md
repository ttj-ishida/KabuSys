# Changelog

すべての重要な変更点を記録します。本プロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [0.1.0] - 2026-03-31
初回リリース。日本株自動売買システム「KabuSys」の基盤となる機能群を実装しました。主要な機能はデータ取得・ETL、マーケットカレンダー管理、ファクター計算、ニュースNLP / 市場レジーム判定、環境設定管理などです。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン __version__ = "0.1.0"）。公開モジュールとして data, strategy, execution, monitoring を列挙。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を実装し、カレントワーキングディレクトリに依存しない自動読み込みを提供。
  - .env のパース処理を強化（コメント、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなど）。
  - 自動ロードの優先度: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - 必須設定取得ヘルパー _require と、各種設定プロパティを持つ Settings クラスを提供（J-Quants, kabuステーション, Slack, DBパス, 監視閾値, 環境/ログレベル検証など）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証を実装（想定値以外は ValueError）。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols をソースに、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを判定し ai_scores テーブルへ書き込む機能を実装（score_news）。
  - バッチ処理（最大 20 銘柄/リクエスト）・1銘柄あたりの記事数・文字数トリム制御を実装。
  - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。その他エラーはスキップして継続するフェイルセーフ方針。
  - レスポンスバリデーションを厳格化（JSON 抽出、results 配列検証、code の正規化、スコア数値性と有限値チェック、±1 にクリップ）。
  - テスト容易性のため _call_openai_api をモック差し替え可能に設計。
  - 時間ウィンドウ計算（JST基準の前日15:00〜当日08:30 を UTC に変換する calc_news_window）を実装し、ルックアヘッドバイアスを防止。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し、market_regime テーブルへ冪等書き込みする機能を実装（score_regime）。
  - 1321 の ma200 乖離計算（_calc_ma200_ratio）、マクロニュース抽出（_fetch_macro_news）、LLM 呼び出しとリトライ/フォールバックロジック（_score_macro）を実装。
  - OpenAI クライアントは OpenAI(api_key=...) を用い、JSON 出力を期待。API 失敗時は macro_sentiment=0.0 にフォールバックする設計。
  - ルックアヘッドバイアス対策として内部で date.today() を参照しない方針を採用（呼び出し側が target_date を与える）。

- リサーチ / ファクター群（kabusys.research）
  - ファクター計算モジュール（factor_research）を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を計算。データ不足時の None 戻り。
    - calc_volatility: 20日 ATR（atr_20）, atr_pct、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と結合して PER（eps が有効な場合）・ROE を計算。
  - 特徴量探索モジュール（feature_exploration）を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関を計算（有効レコードが 3 未満の場合は None）。
    - rank, factor_summary: ランク化（同順位平均処理）や基本統計量サマリを提供。
  - 実装方針として DuckDB 接続を受け取り、外部APIや pandas に依存しない純粋SQL/Python実装を採用。

- データ基盤（kabusys.data）
  - calendar_management: market_calendar を扱うユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。DB 登録がない場合は曜日ベースのフォールバックを採用。
    - calendar_update_job: J-Quants API から差分フェッチして market_calendar を冪等更新する夜間バッチ処理を実装。バックフィル・健全性チェックあり。
  - ETL / パイプライン（data.pipeline, data.etl）
    - ETLResult データクラスを公開し、ETL 実行結果の集約・シリアライズ(to_dict) を提供。
    - pipeline モジュールのインターフェース（差分更新、品質チェック、id_token 注入などの設計方針）を実装。
  - jquants_client など外部クライアントモジュールを想定するインターフェース呼び出しを配置（実装は別モジュールに分離）。

### Changed
- 初版のため「変更」はありません（新規機能追加中心のリリース）。

### Fixed
- 初版のため「修正」はありません（既知のフェーズ）。

### Security
- OpenAI API キーは関数引数で注入可能にし、環境変数に依存しすぎない設計（テスト容易性・キー漏洩リスク低減の観点）。

### Design / Implementation Notes（設計メモ）
- ルックアヘッドバイアス回避のため、AI やスコア関連の関数は内部で datetime.today() / date.today() を直接参照せず、必ず外部から target_date を与える設計になっています。
- OpenAI 呼び出しでは JSON mode を利用し、レスポンスの厳密なパースとバリデーションを行っています。API 障害時は例外をあげずフォールバックする実装方針（フェイルセーフ）。
- DuckDB に対する SQL は互換性・パフォーマンスを考慮して設計。部分更新（DELETE → INSERT）により部分失敗時の既存データ保護を行う。
- テスト容易化: OpenAI 呼び出し部分や内部ユーティリティは unittest.mock で差し替え可能な設計にしています。

### Known issues / Notes
- src/kabusys/data/pipeline.py の末尾にある _get_max_date 関数実装の末尾でコードが途切れている（`return date.fro` のようなタイポ／未完了の行が存在）。ETL 周りの一部ユーティリティ関数が不完全のため、ETL の完全な動作確認および単体テストでの修正が必要です。
- パッケージ __all__ に monitoring が含まれますが、提示されたコード内に monitoring モジュールの実装は含まれていません。実装／公開を今後追加する必要があります。

---

今後の予定（例）
- pipeline の未完了箇所修正と ETL 完全化、単体テスト追加
- monitoring モジュールの実装（プロセス監視・Slack 通知連携など）
- strategy / execution の実装（売買ロジック・注文発注層の安全化）
- ドキュメント（API 使用例、運用手順、環境変数サンプル .env.example）の整備

（必要であれば、この CHANGELOG を元にリリースノートやリリースチェックリストを作成します。）