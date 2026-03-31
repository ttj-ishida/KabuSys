# Changelog

すべての注目すべき変更をこのファイルに記載します。
このプロジェクトは Keep a Changelog のフォーマットに従います。
バージョン番号は SemVer に従います。

## [0.1.0] - 2026-03-31

### Added
- 初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。
- パッケージメタ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として公開。
  - パッケージ公開 API に data/strategy/execution/monitoring を含める設定（`__all__`）。
- 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を自動ロードする機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み順序: OS環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - .env パーサの強化:
    - `export KEY=val` 形式のサポート。
    - シングル/ダブルクォートとバックスラッシュエスケープ対応。
    - コメント処理（クォート外での `#` の取り扱い）に細かな挙動制御。
  - 環境変数必須チェック用 `_require` と、各種設定プロパティ提供（J-Quants, kabuステーション, Slack, DBパス, 監視閾値, 実行環境・ログレベル検証など）。
  - 環境値の妥当性検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）とユーティリティフラグ（is_live 等）を実装。
- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を元に銘柄ごとのニュースを集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（ai_score）を取得して ai_scores テーブルへ書き込む処理を実装。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ `calc_news_window` を実装。
    - バッチサイズ、1銘柄あたりの記事数上限、文字数上限等のスロットリング対策を実装（バッチ最大 20 銘柄、記事最大 10 件、文字数 3000 文字等）。
    - OpenAI への API 呼び出しは JSON Mode を利用し、レスポンスの厳密なバリデーションとスコアの ±1.0 クリップを行う。
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライと、非再試行エラーのスキップ方針を実装。フェイルセーフとして API 失敗時は対象銘柄をスキップして残りを処理。
    - DuckDB の executemany に関する既知制約（空リスト不可）を考慮して保存ロジックを実装（部分更新で他銘柄の既存スコア保護）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を算出する実装を提供。
    - ma200_ratio の算出、マクロニュース抽出、OpenAI 呼び出し（gpt-4o-mini）によるセンチメント評価、スコア合成、market_regime テーブルへの冪等的書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 呼び出し失敗時には macro_sentiment=0.0 として継続するフェイルセーフを設定。
    - OpenAI クライアント呼び出しはモジュール内で独立実装し、テスト容易性のため差し替え可能（ユニットテストでの patch を想定）。
- リサーチ（kabusys.research）
  - factor_research: モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）計算を DuckDB SQL ベースで実装。結果は (date, code) をキーとした dict のリストで返却。
  - feature_exploration: 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman）計算、ファクター統計サマリー、ランク変換ユーティリティを実装。ランクは同順位に対して平均ランクを付与（丸めによる ties 回避）。
  - research パッケージの public API として上述関数を再エクスポート。
- データ平台（kabusys.data）
  - カレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定、next/prev_trading_day、get_trading_days、is_sq_day 等のユーティリティを実装。
    - DB にカレンダーがない場合は曜日ベース（平日を営業日）でフォールバックする一貫した設計。
    - カレンダー夜間更新ジョブ `calendar_update_job` を実装（J-Quants API から差分取得、バックフィル、健全性チェック、冪等保存）。
  - ETL パイプライン（pipeline / etl）
    - ETL 実行結果を表現する `ETLResult` dataclass を実装（取得件数、保存件数、品質チェック結果、エラー一覧など）。
    - pipeline モジュールは差分更新、バックフィル、品質チェック（quality モジュール）との統合を想定した設計。
    - `kabusys.data.etl` で `ETLResult` を再エクスポート。
  - DuckDB を前提とした各種 SQL ベースの処理実装（互換性考慮の実装ノウハウを取り入れた実装）。
- ロギングとエラーハンドリング
  - 各モジュールで詳細な logger 呼び出しを追加。API 呼び出し失敗、DB ロールバック失敗などで適切に警告/例外処理を行う設計。

### Changed
- （初回リリースにつき該当なし）

### Fixed
- （初回リリースにつき該当なし）

### Known limitations / Notes
- OpenAI API の利用は環境変数 `OPENAI_API_KEY` または各関数の `api_key` 引数が必要。未設定の場合は ValueError を送出する。
- timezones: news / calendar の時間窓は UTC naive datetime で扱う設計（JST ↔ UTC の変換ルールを明示）。
- DuckDB の execute/executemany の挙動差（空リスト不可など）へ対処済みだが、使用する DuckDB のバージョンによって挙動差があり得る点に留意。
- 一部外部クライアント（jquants_client 等）の実装は本リリースに含まれないため、実行には別途クライアント実装またはモックが必要。
- LLM レスポンスのパースは堅牢化されているが、期待外のフォーマットが返ると当該チャンク・銘柄はスキップされる（フェイルセーフ設計）。
- 全体設計方針として「ルックアヘッドバイアス回避」のため内部で datetime.today()/date.today() を直接参照しない実装方針を採用。処理の基準日は必ず引数として渡す必要がある。

---

今後のリリースでは以下を予定しています（例）
- strategy / execution / monitoring パッケージの実装拡充（売買戦略の運用ロジック、注文管理、監視アラート）
- テストカバレッジの拡充（API モックを使ったユニットテスト）
- パフォーマンス最適化（大規模データ処理時のメモリ・クエリ最適化）
- ドキュメント・使用例の追加（デプロイ手順、環境変数テンプレート等）

（注）本 CHANGELOG は提供されたコードベースの内容から推測して作成しています。実際の変更履歴やコミット単位の記録はリポジトリのコミットログを参照してください。