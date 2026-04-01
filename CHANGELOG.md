# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
リリース日や詳細はソースコードから推測して記載しています。

全般的な方針：
- ルックアヘッドバイアスを避けるため、各モジュールは datetime.today()/date.today() を直接参照しない設計になっています（呼び出し側から target_date を渡す設計）。
- DuckDB を主要なストレージ層として想定した実装／互換性配慮が盛り込まれています（executemany の空リスト制約などの扱いを明示）。
- OpenAI（gpt-4o-mini）の JSON Mode を用いた LLM 呼び出しを行う機能が含まれます。API 呼び出しはリトライ・バックオフ等の堅牢化を行っています。

## [0.1.0] - 2026-04-01 (初回リリース)
初期リリース。主要機能を実装しました。

### Added
- パッケージ基礎
  - パッケージ初期化: kabusys/__init__.py（バージョン "0.1.0"、公開サブパッケージ定義）。
- 設定・環境変数管理
  - kabusys.config:
    - .env ファイル自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理など。
    - Settings クラスでアプリ設定をプロパティとして提供（J-Quants / kabuステーション / Slack / DB パス / モニタリング閾値 / 環境モード / ログレベル等）。
    - 必須環境変数未設定時は明確な例外を投げる（_require）。
- データプラットフォーム（Data）
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - calendar_update_job: J-Quants からの差分取得と market_calendar テーブルへの冪等更新。バックフィルや健全性チェック（未来日の閾値）を実装。
    - DB 未登録日のフォールバックは曜日ベース（土日非営業日）。
    - 最大探索範囲制限（_MAX_SEARCH_DAYS）により無限ループ防止。
  - kabusys.data.pipeline:
    - ETLResult データクラスを実装（ETL の取得数・保存数・品質問題・エラー等を格納）。
    - ETL の一般設計／ユーティリティ（最大日付取得、テーブル存在確認など）の下地実装。
  - kabusys.data.etl: ETLResult の再エクスポート。
  - DuckDB 互換性に関する配慮（空の executemany を回避するチェック等）。
- 研究（Research）
  - kabusys.research:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を計算。
      - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
      - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS 不在時は None）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン先の将来リターンを計算（horizons の検証あり）。
      - calc_ic: Spearman（ランク）による Information Coefficient を計算（最小レコード数チェックあり）。
      - rank: 同順位は平均ランクで扱うランク関数（浮動小数の丸めで ties の誤差を低減）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
- AI（LLM）機能
  - kabusys.ai.news_nlp:
    - score_news:
      - raw_news と news_symbols を元に銘柄ごとの記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode へバッチ送信してセンチメント（-1.0〜1.0）を算出。
      - チャンクサイズ、記事/文字数トリム、最大リトライ（429/ネットワーク/5xx 共通）、レスポンスバリデーション（results キー存在、型チェック、未知コード無視、数値検証）を実装。
      - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
      - タイムウィンドウ定義: JST 前日 15:00 ～ 当日 08:30（UTC に変換して DB 比較）。
      - API キーは引数または環境変数 OPENAI_API_KEY で指定。
      - API 呼び出しはテスト時に差し替え可能（_call_openai_api を patch 可能）。
  - kabusys.ai.regime_detector:
    - score_regime:
      - ETF 1321（Nikkei225 連動 ETF）の 200 日 MA 乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込み。
      - マクロ記事は raw_news からマクロキーワードで抽出（キーワード一覧を定義）。
      - OpenAI 呼び出しのリトライ/バックオフやフェイルセーフ（API 失敗時は macro_sentiment=0.0）を実装。
      - レジーム算出式や閾値（BULL/BEAR）を定義し、冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
      - API キーは引数または環境変数 OPENAI_API_KEY。
- その他実装上の配慮・ユーティリティ
  - 各所で DuckDB の日付型や NULL の取り扱いを明示的に処理（_to_date 等）。
  - OpenAI 呼び出しに関しては 30 秒のタイムアウト指定、temperature=0、JSON Mode を利用。
  - ロギングを適切に配置（info/debug/warning/exception）。
  - テスト容易性を考慮して API 呼び出し部分の差し替え可能性を確保（内部関数を patch 対象にしている）。

### Changed
- （初回リリースのため変更なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Known issues / 注意点
- OpenAI API
  - OPENAI_API_KEY が未設定の場合、score_news / score_regime は ValueError を投げます。テスト時は明示的に api_key を渡すか環境変数を設定してください。
  - LLM レスポンスは常に正しい JSON とは限らないため、news_nlp では最外側の {} を抽出してパースを試みる等の耐性を持たせていますが、完全な保証はありません。
- DuckDB に依存する実装上の制約
  - DuckDB のバージョン差異によりリスト型バインドや executemany の振る舞いが異なるため、空リストでの executemany 実行を避けるガードを入れています。
- .env 自動読み込み
  - 自動ロードはプロジェクトルートを .git または pyproject.toml から推定します。配布後や特殊環境下でルートが特定できない場合は自動ロードをスキップします（必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください）。
- フェイルセーフ設計
  - AI 呼び出し失敗時は 0.0 にフォールバック（news_nlp/regime_detector）するなど、ETL やスコアリングは可能な限り継続しますが、部分失敗時のデータ整合性に注意してください（ai_scores の置換は取得に成功したコードのみを対象とします）。
- 日時/タイムゾーン
  - 全モジュールは内部で timezone-aware な現在時刻に依存しない設計（target_date を明示的に与える）です。news のウィンドウ計算は JST を基準として UTC naive datetime で DB と比較します。

### Implementation notes（実装上の備考）
- LLM モデル: gpt-4o-mini を想定。JSON Mode（response_format={"type": "json_object"}）を使用。
- リトライ設計: 一般に指数バックオフ（base=1s, 2^attempt）で最大リトライ回数を設定（_MAX_RETRIES=3 等）。
- テストしやすさ: OpenAI 呼び出し箇所は内部関数をモック可能にしており、ユニットテストで外部依存を切り離せます。

---

今後の予定（想定）
- ETL pipeline の細かなステップ（prices / financials / calendar の具体的な差分取得・保存ロジック）の完成・公開。
- 追加のファクター（PBR・配当利回り等）やモデル評価ツールの拡充。
- エンドツーエンドテスト・CI の整備およびドキュメント追加。

この CHANGELOG はコードベースから推測して作成しています。追加情報や実際のリリース日・バージョン方針に応じて更新してください。