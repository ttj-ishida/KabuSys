# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点は下記の通りです。

### Added
- パッケージメタ情報
  - kabusys パッケージ初期化（src/kabusys/__init__.py）とバージョン設定 (0.1.0)。

- 環境設定・自動.env読み込み（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（OS 環境変数を保護する保護リスト付き）。
  - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
  - 標準的な.env構文に対応（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理）。
  - override / protected オプションを持つ読み込み関数。
  - Settings クラスを導入し、J-Quants / kabuステーション / Slack / DB パス / 環境（development/paper_trading/live） / ログレベル等をプロパティ経由で取得可能に。
  - 必須環境変数未設定時にわかりやすい例外を投げる _require() を実装。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。

- データプラットフォーム（DuckDB ベース）のユーティリティ
  - ETL 結果データクラス ETLResult（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - 取得/保存件数、品質チェック結果、エラー一覧を保持。has_errors / has_quality_errors 等のユーティリティを提供。
  - 市場カレンダー管理モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定とユーティリティ:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DBにデータがない場合は曜日ベース（週末除外）のフォールバックを採用。
    - calendar_update_job による J-Quants API からの夜間差分取得と冪等保存（バックフィル & 健全性チェック付き）。
    - 最大探索日数やバックフィル日数等の安全ガードを実装。
  - ETL パイプライン補助（src/kabusys/data/pipeline.py）
    - 差分取得、保存、品質チェック方針を反映したユーティリティ（内部ユーティリティ関数を含む）。
    - DB テーブル存在確認、最大日付取得などのヘルパー実装。

- 研究（Research）モジュール（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m / mom_3m / mom_6m, ma200_dev（200日移動平均乖離）を計算する calc_momentum。
    - ボラティリティ / 流動性: atr_20, atr_pct, avg_turnover, volume_ratio を計算する calc_volatility。
    - バリュー: PER, ROE を計算する calc_value（raw_financials と prices_daily を組み合わせる）。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算。
    - データ不足時や条件を満たさない場合は None を返す設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関を実装、サンプル数不足時は None）。
    - ランク付けユーティリティ: rank（同順位は平均ランク）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median を計算）。
    - 外部ライブラリ依存を避け、標準ライブラリ + DuckDB のみで実装。

- AI（OpenAI）を用いたニュース処理（src/kabusys/ai/）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとにニュースを結合して OpenAI（gpt-4o-mini）へ送信。
    - チャンクバッチ処理（デフォルト最大 20 銘柄/チャンク）、記事数/文字数制限でトークン肥大化対策。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）をエクスポネンシャルバックオフで実装。
    - レスポンスの堅牢なバリデーションとスコアの ±1.0 クリップ。
    - DuckDB への書き込みは部分置換（対象コードのみ DELETE → INSERT）で冪等性と部分失敗耐性を実現。
    - calc_news_window ユーティリティにより JST の時間窓（前日 15:00 ～ 当日 08:30）を UTC に変換して扱う。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - テスト容易性のため _call_openai_api を分離（モック可能）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）を行う score_regime。
    - _calc_ma200_ratio, _fetch_macro_news, _score_macro 等の内部関数を提供。
    - OpenAI 呼び出しは専用の実装を持ち、レスポンスパース失敗や API 障害時はフェイルセーフで macro_sentiment=0.0 を採用。
    - 冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）。
    - ルックアヘッドバイアス防止のため datetime.today() を参照しない設計。

- パブリック API エクスポート
  - ai モジュールで score_news を公開（src/kabusys/ai/__init__.py）。
  - research パッケージで主要な関数を再エクスポート（src/kabusys/research/__init__.py）。
  - data.etl は ETLResult を再エクスポート（src/kabusys/data/etl.py）。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- 決定的なバグ修正履歴はなし（初版のため実装上の安全対策を多数採用）
  - .env 読み込みでファイル読み込み失敗時に警告を出してスキップするようにした（環境に優しい挙動）。
  - OpenAI レスポンスパースで JSON 前後ノイズを許容して最外側の {} を抽出するロバスト化（news_nlp）。
  - DuckDB executemany の空リストバインド問題を回避するため空チェックを導入（ai/news_nlp.py の書き込みロジック）。
  - API エラーの status_code 存在有無に対応する堅牢なエラーハンドリング（openai SDK の仕様差に耐性）。

### Removed
- （初回リリースにつき該当なし）

### Security
- セキュリティ向け注意点
  - OpenAI API キーや各種トークンは Settings 経由で環境変数から取得する設計。不要にログへ出力しないよう配慮。
  - .env の自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD によって無効化可能（テストや CI での秘匿対策）。

### Notes / 実装方針（重要）
- ルックアヘッドバイアス対策:
  - AI・研究関連機能は内部で datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取る設計。
  - DB クエリは date < target_date 等の排他条件を用いてルックアヘッドを防止。
- 冪等性:
  - DB 保存処理は冪等（DELETE→INSERT や ON CONFLICT を想定）により再実行可能。
- フェイルセーフ:
  - 外部 API 障害時は処理を継続する（スコアを 0 にフォールバック、該当チャンクをスキップ等）ことで全体パイプラインの停止を回避。
- テスト容易性:
  - OpenAI 呼び出しはモジュール内関数で切り出し、unittest.mock などで差し替え可能。

---

破壊的変更や既知の制約については今後のバージョンで追記します。問題・改善提案やバグ報告は issue をお立てください。