CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは「Keep a Changelog」フォーマットに準拠しています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース。日本株向けの研究・データ基盤・AI支援・運用補助機能を含むパッケージを追加。
  - パッケージエントリポイント
    - kabusys.__version__ = "0.1.0" として公開。
    - kabusys パッケージから data/strategy/execution/monitoring を __all__ で再エクスポート。
  - 環境設定
    - kabusys.config: .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を使用）。
    - .env パーサを実装。export プレフィックス、シングル/ダブルクォート中のバックスラッシュエスケープ、コメント処理などに対応。
    - OS 環境変数を保護する protected オプションを実装し、.env.local による上書き挙動を提供。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプションを提供。
    - Settings クラスを実装し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で取得。env / log_level の値検証（許容値チェック）を追加。
  - AI（ニュース NLP / レジーム判定）
    - kabusys.ai.news_nlp.score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメント（ai_score）を算出し ai_scores テーブルへ書き込む機能を実装。
      - JST ベースのニュースウィンドウ計算（前日 15:00 JST ~ 当日 08:30 JST）を提供（calc_news_window）。
      - バッチサイズ、記事数・文字数トリム、JSON Mode による厳密 JSON 出力期待、レスポンスバリデーション（results フォーマット、コード/スコア検証）、スコア ±1.0 クリップを実装。
      - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
      - テスト容易性のため _call_openai_api を patch で差し替え可能に設計。
      - DuckDB の executemany に対する互換性配慮（空リストを渡さないガード）。
    - kabusys.ai.regime_detector.score_regime: ETF(1321) の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルに冪等書き込みする機能を実装。
      - ma200_ratio の算出（target_date 未満のデータのみ利用してルックアヘッド防止）。
      - マクロキーワードによる raw_news タイトル抽出、OpenAI による macro_sentiment 評価、API エラー時は 0.0 にフォールバックするフェイルセーフ。
      - レジームスコアの合成・ラベル付与（bull/neutral/bear）とトランザクション（BEGIN/DELETE/INSERT/COMMIT）による冪等保存。
  - Data（ETL / カレンダー等）
    - kabusys.data.pipeline, ETLResult: ETL パイプラインの結果を表すデータクラス ETLResult を公開。
      - 差分取得・バックフィル・品質チェック（quality モジュールを利用）の設計に沿った実装。
      - エラー有無判定プロパティ（has_errors, has_quality_errors）と辞書化メソッド to_dict を提供。
    - kabusys.data.calendar_management: JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の API を提供。
      - market_calendar が空の場合は曜日ベースのフォールバックを用いる一貫した挙動。
      - calendar_update_job により J-Quants からの差分取得と保存（バックフィル、健全性チェック、save_market_calendar 呼び出し）を実装。
    - jquants_client を介したデータ取得・保存を想定した ETL 基盤を実装（差分取得、保存、品質チェックの流れ）。
  - Research（因子計算 / 特徴量探索）
    - kabusys.research.factor_research: モメンタム / ボラティリティ / バリュー等の定量ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。
      - DuckDB SQL を活用し、営業日ベースのラグ/移動平均/ATR/出来高等を正確に計算。
    - kabusys.research.feature_exploration: 将来リターンの計算（calc_forward_returns）、IC（calc_ic）、ランク変換、統計サマリー（factor_summary）などを実装。
      - スピアマン（ランク相関）実装、同順位は平均ランクで処理。
    - research パッケージはデータ系ユーティリティ（zscore_normalize など）を再エクスポート。
  - その他ユーティリティ
    - DuckDB に対する型変換ユーティリティやテーブル存在確認など内部関数を多数実装。
    - OpenAI 呼び出し時に response_format={"type":"json_object"} を利用して JSON Mode を想定。

Changed
- 設計上の決定・注意点として明確化（初期実装段階）
  - 全てのモジュールで datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス防止）。target_date を外部から注入するインターフェースを採用。
  - OpenAI 呼び出しは各モジュールで独立実装し、モジュール間で private helper を共有しない（結合度低減）。
  - DB 書き込みは可能な限り冪等化（DELETE→INSERT、ON CONFLICT を想定）して部分失敗時に既存データを保護。
  - DuckDB のバージョン互換性を考慮して executemany の空リスト渡しを避けるガードを追加。

Fixed
- レスポンスパース時の堅牢性向上
  - JSON Mode でも前後に余計なテキストが混入するケースを考慮し、最外の { ... } を抽出してパースする復元ロジックを追加（news_nlp/_validate_and_extract）。
- OpenAI API エラー分類とリトライ
  - APIError の status_code が存在しない可能性に対応して getattr で安全に取得し、5xx 系は再試行、その他はフォールバックする処理を実装。
- 環境変数パーサの改善
  - クォート内のバックスラッシュエスケープを正しく扱う実装、コメントの扱い改善、無効行の無害化などを実装。

Security
- 環境変数ロード時の保護
  - OS 環境変数を protected として .env による意図せぬ上書きを防止する挙動を導入。
- API キー取り扱い
  - OpenAI API キーは明示的に api_key 引数で注入可能。未設定時は環境変数 OPENAI_API_KEY を参照し、未設定なら ValueError を発生させることで誤動作を防止。

Notes / テスト性
- 多くの箇所でテスト容易性を考慮（_call_openai_api を patch で差し替え可能、api_key を注入可能、KABUSYS_DISABLE_AUTO_ENV_LOAD による副作用抑制など）。
- フェイルセーフ設計により、外部 API 障害時も処理全体を停止させずに中立値やスキップで継続できるようになっている（運用での耐障害性を優先）。

Deprecated
- なし

Removed
- なし

Acknowledgements
- 本リリースは DuckDB、OpenAI SDK、J-Quants 想定 API クライアントとの連携を前提に設計されています。