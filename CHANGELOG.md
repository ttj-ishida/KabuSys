# Changelog

すべての注目すべき変更点を列挙します。フォーマットは「Keep a Changelog」に準拠しています。

※初回公開相当のリリースノートは、コードベースから推測して記載しています。

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システム (KabuSys) のコアモジュール群を導入します。以下の機能を含みます。

### Added
- パッケージ基礎
  - パッケージ初期化（src/kabusys/__init__.py）。バージョン情報 `__version__ = "0.1.0"` と公開サブパッケージ定義。
- 設定・環境変数管理（src/kabusys/config.py）
  - プロジェクトルート検出機能（.git または pyproject.toml を起点に探索）を実装し、CWD に依存しない .env 自動ロードを提供。
  - .env / .env.local の読み込み順序をサポート（OS 環境変数を保護する仕組みを提供）。
  - .env パーサの実装：`export KEY=val`、シングル/ダブルクォート内のエスケープ、行内コメント処理などを考慮。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）をサポート。
  - Settings クラスによる型付きアクセサ（J-Quants / kabu API / LINE / DB / モニタリング / システム設定）。以下のバリデーションを実装：
    - 必須環境変数要求 (`_require`) → 未設定時に ValueError を送出。
    - `PAPER_FILL_MODE` の有効値検証（instant|partial|never|reject）。
    - `KABUSYS_ENV`（development|paper_trading|live）および `LOG_LEVEL`（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検証。
    - Path 型プロパティ（duckdb/sqlite/pid/kill flag 等）とフラグのデフォルト値を明確化。
- AI ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news / news_symbols から銘柄別にニュースを集約して OpenAI（gpt-4o-mini）へ送信し、銘柄別センチメント（ai_score）を ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ計算（JST 前日 15:00 ～ 当日 08:30 を UTC に変換）を提供する `calc_news_window`。
  - バッチ処理（1 回あたり最大 20 銘柄）、1 銘柄あたりの記事数・文字数上限（トリム）によるトークン肥大化対策。
  - JSON Mode を利用した厳密な JSON レスポンス検証（レスポンスの前後に余計なテキストが混入するケースへの復元ロジック含む）。
  - 再試行（429/ネットワーク/タイムアウト/5xx）を伴うエクスポネンシャルバックオフ実装。失敗時は個別チャンクのスキップとフェイルセーフ。
  - スコアの ±1.0 クリップ、部分成功時に既存データを破壊しない（DELETE→INSERT を code 単位で実行、DuckDB の executemany 仕様に配慮）。
  - テスト容易性のため、内部の OpenAI 呼び出し関数（_call_openai_api）を patch 可能に設計。
- AI 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（Nikkei 225 連動型）の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を算出し、market_regime テーブルへ冪等書き込みする `score_regime` を実装。
  - MA 計算は target_date 未満のデータのみを使用してルックアヘッドを防止。
  - マクロニュースの抽出、LLM でのセンチメント評価（json パース・再試行・フェイルセーフ）を含む。
  - 設計上、API 失敗時は macro_sentiment=0.0 を用いるフェイルセーフを採用。
- 研究（research）モジュール（src/kabusys/research/*）
  - factor_research: モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク変換ユーティリティ（rank）を実装。
  - 実装方針として DuckDB 接続を受け取り SQL＋純標準ライブラリで完結する設計（外部APIや pandas に依存しない）。
  - 計算はルックアヘッドバイアスを避けるよう target_date を明示的に受け取る設計。
- データプラットフォーム（src/kabusys/data/*）
  - calendar_management: market_calendar に基づく営業日判定・次/前営業日取得・期間内営業日の取得・SQ日判定ロジックを実装。market_calendar が無い場合は曜日フォールバック（平日＝営業日）。夜間バッチ更新ジョブ（calendar_update_job）を実装（J-Quants クライアント呼び出し、バックフィル、サニティチェック、冪等保存）。
  - pipeline / etl: ETL パイプラインの設計を反映したユーティリティ（ETLResult の公開、ETLResult の to_dict など）。差分更新、バックフィル、品質チェックの概念をコードに反映。
  - jquants_client 経由での fetch/save を想定した設計（クライアント呼び出しの例外ハンドリングとログ出力）。
- DuckDB を前提とした DB 操作
  - 多くのモジュールで DuckDB 接続（DuckDBPyConnection）を直接受け取り SQL 実行する実装。一貫して BEGIN/COMMIT/ROLLBACK を用いたトランザクション管理を実装。
  - DuckDB に対する実装細部（executemany の空リスト制約など）への互換性対策を実施。
- ロギングと堅牢性
  - 各処理で詳細な logger.debug/info/warning/exception を追加。外部 API 失敗時はフェイルセーフでスコアや処理を続行する設計（例: news/regime は API 失敗時 0.0 フォールバック）。
- テスト性向上
  - OpenAI への実際の呼び出しをモックできる設計（内部 _call_openai_api の patch によりテスト可能）。
  - API キー注入（api_key 引数）により環境依存を低減。

### Changed
- （初回リリースのため該当無し）

### Fixed
- （初回リリースのため該当無し）

### Security
- 環境変数の読み込みで OS 環境（既存のキー）を保護する仕組みを導入（.env による上書きを制御）。.env.local の上書き挙動は明示的。

### Notes / Design Decisions
- ルックアヘッドバイアス対策: 各 AI / 研究モジュールは内部で datetime.today()/date.today() を参照せず、必ず caller が与える target_date のみを基準に計算する設計。
- API の冗長性: LLM 呼び出しは再試行・バックオフ・フェイルセーフを組み合わせて安定性を高める（429 / ネットワーク / タイムアウト / 5xx を考慮）。
- DB 書き込みの冪等性: market_calendar / ai_scores / market_regime 等は既存行を削除してから挿入する、または ON CONFLICT で上書きする運用を想定。
- DuckDB バージョン差異に配慮した実装（list バインドの不安定性への対処等）。

---

将来のリリースでは以下のような項目が想定されます（参考）:
- jquants_client の具体実装と認証フローの追加
- モニタリング・実行（execution/monitoring）サブパッケージの実装詳細
- テストカバレッジ・CI 設定・ドキュメント充実
- 性能最適化・大規模データ処理におけるメモリ/CPU 対策

（以上）