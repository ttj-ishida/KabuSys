Keep a Changelog に準拠した形式で、提示されたコードベースから推測できる変更履歴を日本語で作成しました。初回リリースとして v0.1.0 を想定し、実装されている主要な機能・設計方針・重要な実装上の注意点を列挙しています。

CHANGELOG.md
=============
全般ルール: https://keepachangelog.com/ja/1.0.0/

@section: [0.1.0] - 2026-04-03
--------------------------------
Added
- 初回リリース: KabuSys — 日本株自動売買システムのコアモジュール群を追加。
  - パッケージのエントリポイント: kabusys (version = 0.1.0)。公開サブパッケージ: data, strategy, execution, monitoring。
- 環境・設定管理 (kabusys.config)
  - .env ファイルと環境変数の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - .env パーサ: export KEY= 候補のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理の取り扱いを実装。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を導入。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視閾値 / 環境種別・ログレベル等の設定 accessor を定義。必須項目取得時のエラー報告（_require）を実装。
  - 環境値検証: KABUSYS_ENV および LOG_LEVEL の許容値検査を実装。
- AI (kabusys.ai)
  - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのニュースセンチメント（ai_scores）を生成・DuckDB に書き込む一連処理を実装。
    - タイムウィンドウ計算、記事トリミング（記事数・文字数制限）、バッチ処理（最大20銘柄/回）、レスポンス検証、±1.0 でのクリップ、DB への冪等的置換（DELETE→INSERT）を実装。
    - API リトライ（429/接続断/タイムアウト/5xx）、指数バックオフ、失敗時のフェイルセーフスキップの実装。
    - テスト容易性のため API 呼び出し関数をパッチ差替可能に設計。
  - regime_detector.score_regime: ETF（1321）200日移動平均乖離とマクロニュース（ニュース NLP 結果）を重み付けして日次の market_regime を算出・保存するモジュールを実装。
    - ma200_ratio 計算、マクロニュース抽出、OpenAI 呼び出し、スコア合成、ラベル付与（bull/neutral/bear）、冪等 DB 書き込みを実装。
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。
    - OpenAI クライアントは明示的に注入（環境変数 or 引数）する方式。
- Data (kabusys.data)
  - calendar_management: JPX マーケットカレンダー管理の実装（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day、カレンダー未取得時は曜日ベースのフォールバック）。
    - calendar_update_job: J-Quants からの差分取得と冪等保存、バックフィル、健全性チェックを実装。
    - DB がまばらな場合でも一貫性を保つ設計（DB 値優先・未登録日は曜日フォールバック）。
  - pipeline / etl:
    - ETLResult データクラスを公開（ETL 実行結果の集約、品質問題とエラー列挙、辞書化ユーティリティ）。
    - ETL の設計方針・ユーティリティ（テーブル存在確認、最大日付取得等）の基礎実装（差分更新、J-Quants クライアント呼び出し、品質チェック連携を想定）。
  - jquants_client を経由する想定の差分取得・保存フローに対応するための補助機能を追加。
- Research (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を DuckDB の SQL により高速に計算。
    - calc_volatility: 20日 ATR（true range の厳密扱い）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE 計算（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時の None 戻し。
    - rank / factor_summary: ランク変換（同順位は平均ランク）・基本統計量の算出を純粋 Python で実装。外部依存を使わない設計。
  - research パッケージは主要関数を再エクスポートして利用を簡便化。
- 実装全体での注意点（共通設計）
  - ルックアヘッドバイアス対策: 各モジュールは datetime.today()/date.today() を直接参照せず、関数引数として target_date を受け取る設計を徹底。
  - DuckDB を主要なローカル分析 DB として想定。埋め込み SQL と window 関数を多用し、データ処理を DB 側で行う。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 相当を想定）し、トランザクション (BEGIN/COMMIT/ROLLBACK) を使用。
  - OpenAI API 呼び出しは JSON Mode を利用し、レスポンス検証やパースの堅牢化（前後余計文字のトリムなど）を実装。
  - API エラーに対するリトライ戦略（指数バックオフ）と、API 失敗時のフェイルセーフ（スコア=0.0 やスキップ）を導入。
  - テストを意識した設計（API 呼び出し関数をモジュール内で切り替えられる/patch 可能）。

Changed
- 初回リリースのため "Changed" は該当なし。

Fixed
- 初回リリースのため "Fixed" は該当なし。
- 実装上明示的に対処した不具合回避/堅牢性向上:
  - .env 読み込み失敗時に警告を出力して継続する（ファイル I/O の例外ハンドリング）。
  - OpenAI レスポンスパース失敗・数値変換エラーなどで例外伝播させずログに記録してフォールバックする実装。

Security
- 機密情報取り扱い:
  - OpenAI API キー等の機密は引数 injection か環境変数で扱う設計。Settings は必須キー未設定時に ValueError を投げるため起動時の早期検出が可能。
  - .env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト/CI 用）。

Notes / 今後の想定タスク（コードから推測）
- strategy / execution / monitoring パッケージの具象実装（注文発注ロジック、監視プロセス、実行エンジンとの連携）が今後追加される想定。
- ETL パイプラインの完全実装（差分計算の本体、quality モジュール呼び出しの詳細）および jquants_client の具体的実装/テストカバレッジ整備。
- マイグレーション / スキーマ定義・マネジメント（DuckDB スキーマ初期化）周りのドキュメントやユーティリティ整備。
- OpenAI API 使用量削減のためのプロンプト最適化／キャッシュの導入、または代替モデルのサポート。

付記
- 本 CHANGELOG は提示されたソースコードから実装意図・機能を推測して作成しています。実際のコミット履歴やリリースノートに合わせて日付・項目を調整してください。