保持する変更履歴フォーマット: Keep a Changelog 準拠

以下は提供されたコードベースから推測して作成した初回リリースの CHANGELOG.md（日本語）です。

CHANGELOG.md
============

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報 (src/kabusys/__init__.py)
    - __version__ = "0.1.0"
    - 公開サブパッケージ: data, strategy, execution, monitoring

- 環境設定 / .env ローダー (src/kabusys/config.py)
  - .env / .env.local ファイルまたは環境変数から設定を読み込む自動ローダーを実装
  - プロジェクトルート検出ロジック: __file__ の親ディレクトリから .git または pyproject.toml を探索（CWD 非依存）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）
  - .env の行パーサは export 形式、クォート、エスケープ、インラインコメントなどに対応
  - Settings クラスを提供し、各種設定値（J-Quants / kabu / LINE / DB パス / Paper Trading モード / 監視閾値 / 環境種別 / ログレベル等）をプロパティ経由で取得
  - Paper Trading の PAPER_FILL_MODE の検証（instant/partial/never/reject）
  - 環境変数の必須チェック時は明示的な例外を発生 (_require)

- AI モジュール (src/kabusys/ai/*)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を ai_scores テーブルへ保存
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）
    - 1チャンク最大 20 銘柄、1銘柄当たりの記事数と文字数に上限（過度なトークン化防止）
    - OpenAI 呼び出しに対するリトライ（429、ネットワーク断、タイムアウト、5xx）と指数バックオフ
    - レスポンス検証ロジック（JSON 抽出、results 配列、コード照合、数値検証、±1.0 クリップ）
    - 部分失敗に備えた idempotent な DB 書き換え（DELETE → INSERT、対象コード限定）とトランザクション
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api の patch を想定）

  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出
    - prices_daily / raw_news を参照し、market_regime テーブルへ冪等書込み（BEGIN/DELETE/INSERT/COMMIT）
    - OpenAI 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）
    - API 呼び出しに対するリトライ・バックオフ、5xx 判定対応
    - 設計上ルックアヘッドバイアスを防ぐため date 引数を使用し、datetime.today() を参照しない実装方針

- リサーチ（因子・特徴量）モジュール (src/kabusys/research/*)
  - factor_research.py
    - モメンタムファクター: 1M/3M/6M リターン、200 日 MA 乖離を計算（calc_momentum）
    - ボラティリティ/流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比（calc_volatility）
    - バリュー: raw_financials から EPS/ROE を取得し PER / ROE を計算（calc_value）
    - DuckDB を活用した SQL ベースの実装、結果は (date, code) をキーとする dict リストで返却
  - feature_exploration.py
    - 将来リターン計算: 指定ホライズン（デフォルト [1,5,21]）の fwd リターンを計算（calc_forward_returns）
    - IC（Information Coefficient）計算: スピアマンランク相関によるファクター評価（calc_ic）
    - ランク変換ユーティリティ（同順位は平均ランク）(rank)
    - ファクター統計サマリー（count/mean/std/min/max/median）(factor_summary)
    - pandas 等に依存せず標準ライブラリ + DuckDB で実装

- データプラットフォーム（Data）モジュール (src/kabusys/data/*)
  - calendar_management.py
    - JPX カレンダー管理：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - market_calendar が未取得の場合は曜日ベースのフォールバック（例: 土日を非営業日）
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫した振る舞い
    - 夜間バッチジョブ calendar_update_job により J-Quants から差分取得 → 保存（バックフィル・健全性チェック含む）
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL の取得数/保存数、品質問題、エラーの集約）
    - 差分更新・バックフィル・品質チェックの設計方針に対応
    - jquants_client と quality モジュールを利用する想定（外部 API 呼び出しは jquants_client 経由）

Changed
- N/A（初回リリース）

Fixed
- N/A（初回リリース）

Security
- OpenAI API キーの取り扱い
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は ValueError を発生させる（明示的なエラー）。
  - .env ファイル読込は OS 環境変数を保護する仕組み（protected set）を持つ。

Notes (設計上の重要ポイント / フェイルセーフ)
- ルックアヘッドバイアス対策: 日付に関する処理は date 引数を明示して行い、datetime.today()/date.today() を参照しない実装方針を多くのモジュールで採用
- DuckDB を主要なデータストアとして SQL とウィンドウ関数を活用
- API 呼び出しはリトライ + 指数バックオフを基本とし、致命的な例外は上位へ伝播するが多くのケースでフェイルセーフ（スキップして継続）する設計
- DB 書き込みは可能な限り冪等性を確保（DELETE→INSERT や ON CONFLICT を想定）し、トランザクション（BEGIN/COMMIT/ROLLBACK）で整合性保持
- テスト容易性: OpenAI 呼び出し関数をモジュール単位で差し替え可能（patch を想定）

今後の予定（想定 / 推測）
- monitoring, execution, strategy サブパッケージの実装拡張（現状は公開名のみ）
- jquants_client や quality などのインテグレーションモジュールの実装・安定化
- 追加のユニットテスト・CI インテグレーション

以上

（注）この CHANGELOG は提供されたソースコードからの推測に基づいて作成しています。実際のリリースノートに含めたい運用上の注意事項や既知の制限・マイグレーション情報があれば追記してください。