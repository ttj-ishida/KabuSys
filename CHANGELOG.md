# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
フォーマット: 概要 → セクション（Added / Changed / Fixed / Deprecated / Removed / Security）。  
初版リリース: 0.1.0（初期実装）

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主要な追加内容は以下の通りです。

### Added
- パッケージ基盤
  - パッケージルートを定義（src/kabusys/__init__.py）。バージョン定義: __version__ = "0.1.0"。パブリックAPIとして data / strategy / execution / monitoring をエクスポート。

- 設定管理
  - 環境変数・設定読み込みモジュールを実装（src/kabusys/config.py）。
    - .env/.env.local 自動読み込み（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env ファイルパーサは export PREFIX=VALUE 形式、クォート・エスケープ、インラインコメント処理に対応。
    - 上書き制御（override）と protected（OS 環境変数保護）をサポート。
    - Settings クラスを提供し、主要設定プロパティを定義（J-Quants・kabu API・LINE・DB パス・監視閾値・実行環境等）。
    - 環境変数値のバリデーションを実装（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）、不正値は ValueError を送出。

- ニュースNLP（AI）
  - ニュース記事を用いた銘柄単位のセンチメントスコアリング機能を実装（src/kabusys/ai/news_nlp.py）。
    - タイムウィンドウ計算（JST ベース → DB 比較用に UTC naive datetime に変換）。
    - raw_news と news_symbols を集約して銘柄ごとに記事を結合（記事数・文字数の上限トリミング: _MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
    - OpenAI（gpt-4o-mini）へバッチ送信（1回あたり最大 _BATCH_SIZE=20 銘柄）。
    - JSON Mode（厳密 JSON）でレスポンスを期待し、レスポンス検証・パース、スコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ実装。致命的でない障害時はスキップして継続するフェイルセーフ設計。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）、書き込みは冪等的に DELETE → INSERT の順で実施。
    - 公開 API: score_news(conn, target_date, api_key=None) → 書き込み件数を返す。
    - テスト容易性: _call_openai_api をモック差し替え可能（unittest.mock.patch 想定）。

  - calc_news_window(target_date) を公開し、ニュース収集ウィンドウを計算。

- 市場レジーム判定（AI + 指標合成）
  - ETF（1321）200日移動平均乖離とニュースマクロセンチメントを合成して日次市場レジームを判定する機能を実装（src/kabusys/ai/regime_detector.py）。
    - ma200_ratio（最新終値 / 200日MA）を DuckDB から計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードで raw_news のタイトルを抽出し（最大 _MAX_MACRO_ARTICLES）、OpenAI（gpt-4o-mini）でマクロセンチメントを評価。
    - 重み付け合成: 70% * (ma200_deviation) + 30% * macro_sentiment、スコアはクリップしラベル付け（bull / neutral / bear）。
    - API 失敗時は macro_sentiment=0.0 をフォールバック（フェイルセーフ）。
    - DB への保存はトランザクションで冪等書き込み（BEGIN / DELETE / INSERT / COMMIT / ROLLBACK ハンドリング）。
    - 公開 API: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。
    - テスト容易性: news_nlp と異なり独立した _call_openai_api 実装を持ち、モジュール間でプライベート関数を共有しない設計。

- 研究（Research）
  - factor_research（src/kabusys/research/factor_research.py）
    - モメンタムファクター calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、200日MA乖離（ma200_dev）を計算。
    - ボラティリティ/流動性 calc_volatility(conn, target_date): 20日ATR（atr_20）, atr_pct, avg_turnover, volume_ratio を計算。
    - バリュー calc_value(conn, target_date): raw_financials からの EPS/ROE を用いて PER/ROE を算出（欠損/0 の場合は None）。
    - 全関数は prices_daily / raw_financials のみを参照、外部 API へはアクセスしないことを保証。
    - 結果は (date, code) キーの dict リストで返却。

  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns(conn, target_date, horizons=None)（デフォルト: [1,5,21]）を一括 SQL で取得。
    - IC（Information Coefficient） calc_ic(factor_records, forward_records, factor_col, return_col) を実装（Spearman の ρ、同順位は平均ランク）。
    - rank(values) と factor_summary(records, columns) を実装（統計量: count/mean/std/min/max/median）。
    - 計算は標準ライブラリのみで実装、pandas 等に依存しない。

  - research パッケージの __init__ で主要関数を再エクスポート。

- データ基盤（Data）
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定ロジックを実装:
      - is_trading_day(conn, d)、next_trading_day、prev_trading_day、get_trading_days、is_sq_day 等を提供。
    - DB にデータがない場合は曜日ベース（平日日: 営業日、土日: 非営業日）でフォールバック。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日フォールバックで一貫性を保持。
    - calendar_update_job(conn, lookahead_days=90): J-Quants から差分取得して market_calendar を冪等的に更新。バックフィルと健全性チェック（未来日付の異常検出）を実装。
    - DuckDB 型変換ユーティリティとテーブル存在チェックを提供。

  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - ETL の設計方針に基づいた ETLResult データクラスを実装（取得件数、保存件数、品質チェック結果、エラー一覧などを保持）。
    - ETLResult.to_dict() は quality_issues を単純な dict リストへ展開して返却。
    - pipeline モジュールの ETLResult を data.etl で再エクスポート。

  - data パッケージの __init__ で pipeline.ETLResult を再エクスポート (src/kabusys/data/etl.py)。

- 互換性・テスト設計
  - OpenAI 呼び出し部分はテストで差し替えられるよう関数化（_call_openai_api をモック可能）。
  - DuckDB バインドに関する互換性注意（executemany に空リストを渡さない等）を反映。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で渡すか、環境変数 OPENAI_API_KEY を参照する。未設定時は ValueError を発生させ安全に停止する設計。

---

注意事項（実装上の重要ポイント）
- ルックアヘッドバイアス防止: 各モジュールは internal に date.today() を直接参照しない設計。必ず target_date を引数で渡し、DB クエリも target_date の排他条件等で未来データを参照しないように実装しています。
- フェイルセーフ: AI API や外部 API の一時障害時は処理を中断せずに合理的なデフォルト（例: macro_sentiment=0.0）やスキップで継続する設計です。ただし、OpenAI API キー未設定は即時エラーとして扱います。
- DuckDB 周り: executemany に空リストを渡すとエラーになるバージョンがあるため、空チェックを行ってから executemany を実行しています。
- ロギング: 重要な分岐・エラー・警告は logger 経由で出力されます。

今後の予定（例）
- strategy / execution / monitoring の具体的実装（現在はパッケージ公開のみ）。
- J-Quants クライアント周り（fetch/save）の追加実装と ETL パイプラインの統合ジョブ。
- テストカバレッジ拡充と CI パイプライン導入。

---

作者注: 実装内容はソースコードから推測してまとめています。実際の運用方針・ドキュメントと差異がある場合は README や運用ドキュメントを優先してください。