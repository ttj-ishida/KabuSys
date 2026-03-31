# Keep a Changelog — CHANGELOG.md（日本語）

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の方針に従って記載しています。  
バージョン番号はパッケージ内の __version__（src/kabusys/__init__.py）に合わせています。

現在のリリース:
- 0.1.0 — 2026-03-31

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買システムの基盤機能群を実装しました。主に以下のパッケージ・機能を含みます。

### 追加 (Added)
- パッケージ構成
  - kabusys のコアモジュールを提供（data, research, ai, config, 等）。
  - バージョンは 0.1.0。

- 設定・環境変数管理（src/kabusys/config.py）
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得。
  - 必須設定の取得ヘルパ（_require）を実装（不足時は ValueError）。
  - サポートされる設定例:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL 検証
  - .env ファイル自動読込機能を実装（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - 読み込み順: OS 環境 > .env.local > .env（.env.local は override）
    - OS 環境変数を保護する protected 機構を実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）
  - .env パーサは以下に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - クォートなしでのインラインコメント処理（'#' をコメント扱いにする場合のルール）
    - 無効行・コメント行のスキップ
  - プロジェクト配布後でも .__file__ ベースでプロジェクトルートを探索するため CWD に依存しない実装。

- AI 関連（src/kabusys/ai/*）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）を用いてセンチメントを算出し ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST 相当の UTC ウィンドウを計算（calc_news_window）。
    - バッチ処理: 最大 20 銘柄ずつ API 呼び出し（チャンク処理）。
    - 1 銘柄あたり最新記事を上限 10 件・最大 3000 文字にトリム。
    - JSON Mode を使った厳格なレスポンス期待と、実運用を想定した耐障害処理（JSON 前後の余分なテキスト復元処理など）。
    - API の一時障害（429, ネットワーク断, タイムアウト, 5xx）は指数バックオフでリトライ。その他のエラーはスキップして継続。
    - レスポンスのバリデーション（results 配列・code の存在・数値型の score）を実装。無効なレスポンスはそのチャンクをスキップ。
    - 部分成功を許容するため、ai_scores の置換は対象コードのみに対して DELETE → INSERT を実行（部分失敗でも他コードの既存スコアを保護）。
    - テスト容易性: OpenAI 呼び出し関数（_call_openai_api）を unittest.mock.patch で差し替え可能。
    - 空記事時は処理を早期終了（書き込み 0）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で冪等書き込み。
    - マクロニュースは news_nlp.calc_news_window のウィンドウでフィルタし、マクロキーワードで抽出（_MACRO_KEYWORDS）。
    - OpenAI（gpt-4o-mini）を用いたマクロセンチメント評価を行い、API 障害時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアは clip で -1.0〜1.0 に制限ししきい値で bull / neutral / bear を判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理、書き込み失敗時は ROLLBACK を試み例外を上位へ伝播。
    - テスト容易性: 同様に OpenAI 呼び出しを差し替え可能。

- データ基盤（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX マーケットカレンダー用のユーティリティを実装。
    - 営業日判定関数群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得の際は曜日（平日）ベースのフォールバックを使用。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日ベースで一貫した結果を返す実装。
    - calendar_update_job を実装し、jquants_client を使って差分取得（lookahead/backfill/健全性チェック）→ 保存（save_market_calendar）を行う。
    - 最大探索日数やバックフィル期間、健全性最大未来日数などの保護機構を組み込む。
  - ETL パイプライン（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL 実行結果（取得数・保存数・品質問題・エラー一覧など）を一元管理。
    - テーブル存在確認や最大日付取得などのユーティリティを実装。
    - 差分更新 / バックフィル / 品質チェックの設計方針を組み込むための基盤を整備。
    - etl モジュールは pipeline.ETLResult を公開（再エクスポート）。
    - J-Quants からの差分取得・保存は jquants_client を想定して実装（fetch/save 呼び出し）。

- リサーチ（src/kabusys/research/*）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: mom_1m / mom_3m / mom_6m, ma200_dev（200 日 MA 乖離率）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials から最新財務を結合して PER・ROE を計算（EPS 無効時は None）。
    - DuckDB SQL を駆使して営業日ベースの窓処理を実装（LAG/AVG/ROW_NUMBER 等）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）で将来リターンをまとめて取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクを採るランク変換（丸めで ties 対策）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー機能。
    - pandas 等の外部ライブラリに依存せず、標準ライブラリ＋DuckDB で実装。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- なし。

### 削除 (Removed)
- なし。

### セキュリティ (Security)
- OpenAI API の利用には API キー（環境変数 OPENAI_API_KEY または関数引数で注入）が必要。キー管理は適切に行ってください。

### 既知の制約・注意事項 (Known issues / Notes)
- OpenAI API 依存:
  - API 呼び出し失敗時はフェイルセーフとしてスコアを 0.0 にフォールバックしたり、チャンクをスキップします。部分的な欠損が発生する可能性があります。
  - レスポンスは JSON mode を期待していますが、場合によっては前後に余分なテキストが混入することを考慮してパースのリカバリ処理を行っています。
- データ不足時の挙動:
  - MA200 等のための十分な履歴がない銘柄は None（または中立値 1.0）を返す箇所があります（calc_momentum, _calc_ma200_ratio 等）。
- DuckDB 互換性:
  - executemany に空リストを渡すとエラーになるバージョンがあるため、空リストの場合は処理をスキップするガードを入れています。
- 時刻参照の方針:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計が各所で採用されています（target_date を明示的に与える設計）。
- テスト支援:
  - OpenAI 呼び出し部分はモック可能（_call_openai_api を patch）にしてあり、ユニットテストしやすい設計です。
- 要初期設定:
  - .env.example に従って必要な環境変数を設定してください（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK など）。自動 .env ロードはプロジェクトルートの検出に依存します。

### マイグレーション / 導入メモ (Upgrade / Install notes)
- 環境変数を設定（必須項目は Settings._require によりエラーとなる）。
- DuckDB / sqlite 用の初期スキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）を準備してください（このリポジトリにはスキーマ定義ファイルは含まれていません）。
- J-Quants クライアント（jquants_client）を実装または設定し、ETL / calendar_update_job の連携を確立してください。
- OpenAI API の利用に際してはレート制限や課金に注意してください。

---

今後のリリース案（予定）
- ETL の具体的なジョブ統合（差分算出ロジックの可視化、監査ログ）
- モデル（戦略）層の実装（execution/strategy パッケージの充実）
- CI テスト向けの DuckDB テスト用フィクスチャ、より詳細なドキュメント追加

（以上）