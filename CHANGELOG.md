# Changelog

すべての重要な変更点を保守可能な形で記録します。  
この CHANGELOG は Keep a Changelog の形式に準拠しています。  
（内容は提供されたコードベースの実装内容から推測して作成しています）

全般的な注記
- 本リリース記述はソースコード中の実装（モジュール名、関数、挙動、定数、設計方針のコメント等）を元に推測して作成しています。
- DuckDB を主要なローカルデータストアとして利用する設計、OpenAI（gpt-4o-mini）を用いた NLP 処理、および J-Quants / kabu スタンド関連の連携を前提とした機能群が含まれます。

[0.1.0] - 2026-04-02
---------------------------------

Added
- パッケージ初期リリース。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を定義。
  - public API のエクスポート: data, strategy, execution, monitoring を __all__ に追加（各サブパッケージへの入口）。

- 環境設定 / ローダ
  - kabusys.config: 環境変数管理機能を実装。
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の行パーサは export プレフィックス、引用符（シングル/ダブル）、エスケープ、インラインコメントを考慮して堅牢に処理。
    - .env.local は .env を上書きする優先度（override）で読み込まれるが、既存の OS 環境変数は保護（protected）される。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス /監視閾値 / 環境モード・ログレベル等のプロパティ経由で安全に取得可能。
    - KABUSYS_ENV の検証（development / paper_trading / live）や LOG_LEVEL の検証を実装。

- AI（NLP / レジーム判定）
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメント（-1.0〜1.0）を算出し ai_scores テーブルへ書き込む処理を実装（score_news）。
    - タイムウィンドウ計算（JST 基準で前日 15:00 ～ 当日 08:30 の UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・記事上限（_MAX_ARTICLES_PER_STOCK=10、文字トリム _MAX_CHARS_PER_STOCK=3000）・レスポンス検証ロジックを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx のエクスポネンシャルバックオフによるリトライ、その他障害はフェイルセーフでスキップ（例外伝搬しない）する設計。
    - レスポンス検証により未知コード無視、数値パース・有限性チェック、スコアの ±1.0 クリップを実装。
    - テスト容易性のため、OpenAI 呼び出し関数を patch して差し替え可能。

  - kabusys.ai.regime_detector:
    - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する処理を実装（score_regime）。
    - ma200 の計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを排除。
    - マクロニュース抽出はタイトルにマクロキーワードをマッチさせる（_MACRO_KEYWORDS）。
    - OpenAI 呼び出し（gpt-4o-mini）についてリトライロジックと、API 失敗時は macro_sentiment=0.0 とするフェイルセーフを実装。
    - 判定結果は market_regime テーブルへ冪等（BEGIN / DELETE / INSERT / COMMIT）で保存。

- Data / ETL / カレンダー
  - kabusys.data.pipeline / kabusys.data.etl:
    - ETLResult データクラスを実装し、ETL 実行の取得数/保存数、品質問題、エラー一覧などを構造化して返却・ロギング可能に。
    - ETL の基本設計方針（差分更新・バックフィル・品質チェック継続方針）と各種定数を定義。

  - kabusys.data.calendar_management:
    - market_calendar を扱う各種ユーティリティを実装。
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB に market_calendar のデータがある場合は DB 値優先、未登録日は曜日（土日）ベースでフォールバックする一貫した挙動。
    - calendar_update_job: J-Quants から差分取得して market_calendar を更新する夜間バッチ処理。バックフィルや健全性チェック（未来日付閾値）を実装。
    - 最大探索日数 (_MAX_SEARCH_DAYS) により無限ループを防止。

- Research（因子・特徴量解析）
  - kabusys.research.factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR（atr_20）/相対 ATR（atr_pct）/20日平均売買代金/出来高比率を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を算出（PBR 等は未実装）。
    - DuckDB 上の SQL ウィンドウ関数を活用した実装。データ不足時は None を返す仕様。

  - kabusys.research.feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを計算。引数検証あり（1〜252 日）。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード 3 件未満は None）。
    - rank: 平均ランク（同順位は平均）の算出を実装（丸めにより ties の誤差を抑制）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ機能を実装。
    - 外部ライブラリに依存せず標準ライブラリのみでの実装を意図。

- その他
  - OpenAI クライアント生成は API キー注入の柔軟性を持たせており、api_key 引数または環境変数 OPENAI_API_KEY のいずれかで解決。
  - OpenAI 呼び出し箇所はテスト用に差し替え可能に実装されている（ユニットテスト容易化の配慮）。
  - ロギング、警告メッセージ、フェイルセーフ設計（API レスポンスパース失敗や DB 書き込み失敗時のロールバック処理）を多用している。

Changed
- 初回リリースのため該当なし（全て新規追加として実装）。

Fixed
- 初回リリースのため該当なし。ただし、以下の堅牢化・防御的実装を含む点を記載。
  - .env パーサの引用符・エスケープ・コメント処理を強化。
  - OpenAI 呼び出しのリトライ／バックオフ、JSON パース失敗時の復元ロジック（最外の {} 抽出）などの耐障害性向上。
  - DB 書き込み時のトランザクション（BEGIN/COMMIT/ROLLBACK）による冪等処理。

Deprecated
- なし

Removed
- なし

Security
- なし（ただし環境変数（APIキー等）は Settings 経由で取得し、.env の自動読み込みを環境変数で無効化可能にする等、取り扱いに配慮した実装になっています）

Known limitations / 注意点（コードから推測）
- ETL pipeline の一部実装（ファイル末尾付近）でソースが途切れている可能性があるため、実装の続き／テスト確認が必要です（提供ソースの切れに起因）。
- OpenAI API 呼び出しは外部ネットワークに依存するため、実運用では API キー管理やレート制限、費用管理に注意が必要です。
- news_nlp/regime_detector は LLM 出力に強く依存するため、プロダクション導入前にプロンプト調整・レスポンス検証のチューニングを推奨します。
- 現状、PBR や配当利回りなど一部バリューファクターは未実装。

今後の予定（推奨）
- ETL モジュールの完全実装と単体テストの追加。
- end-to-end の統合テスト（DuckDB のテストデータを用いた AI スコアリングと DB 書き込みの検証）。
- Slack / kabu-station 等外部サービス連携箇所の実装確認と監視（retry / circuit-breaker）の追加。
- ドキュメント（API 仕様、運用手順、環境変数一覧 .env.example）を整備。

---
この CHANGELOG はコード内容から推測して作成したため、実際の開発履歴と差異がある可能性があります。正確な変更履歴が必要な場合はコミット履歴（git log）やリリースノートの元ソースを参照してください。