# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このプロジェクトはセマンティックバージョニングを採用しています。  

詳しい方針: https://keepachangelog.com/ (日本語訳に準拠)

## [Unreleased]

（現時点のコードベースは初回リリースに相当するため、Unreleased には保留の項目を記載しません）

## [0.1.0] - 2026-03-31

初回リリース。以下の主要機能とモジュールを実装・公開。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として定義。公開 API として data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト時に利用）。
  - .env ファイルのパース強化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメント処理（クォート有り/無しの差異を考慮）
  - 上書き制御: .env.local は override=True で読み込み、OS 環境変数を protected として上書きを防止。
  - Settings クラスを提供:
    - J-Quants / kabu ステーション / Slack / DB パス等のプロパティ（必須変数は _require で検査）。
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値を限定）。
    - is_live / is_paper / is_dev の便宜プロパティ。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとにセンチメントを評価して ai_scores テーブルへ書き込み。
    - ニュースウィンドウ計算（JST 基準の前日 15:00 ～ 当日 08:30 に対応）を calc_news_window で提供。
    - 1 銘柄あたりの最大記事数・最大文字数トリム、最大バッチサイズ（20銘柄）によるバッチ送信。
    - OpenAI 呼び出しは JSON Mode を利用し、レスポンスを厳密にバリデーションして不正レスポンスはスキップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフでのリトライ実装。
    - テスト容易性: _call_openai_api を patch により差し替え可能。
    - DuckDB の executemany の制約を考慮し、空リストでの実行を避ける処理を実装。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - score_regime(conn, target_date, api_key=None): ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ冪等的に書き込み。
    - ma200_ratio の計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロ記事抽出はマクロキーワード群でフィルタ。記事が無ければ LLM 呼び出しをスキップし macro_sentiment=0.0 とするフォールバック。
    - OpenAI 呼び出しに対するリトライ・エラー処理および JSON パース失敗時のフォールバック（macro_sentiment=0.0）。
    - レジームを 'bull' / 'neutral' / 'bear' に分類する閾値とスコア合成ロジックを実装。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT の冪等処理、失敗時は ROLLBACK を確実に行う実装。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。
    - market_calendar が未取得時の曜日ベースフォールバック（週末を非営業日扱い）を実装し、DB 登録有りの場合は DB 値を優先。
    - next/prev の探索には上限日数を設定して無限ループを防止。
    - calendar_update_job により J-Quants からの差分取得・バックフィル・健全性チェック・保存処理を実装（fetch/save は jquants_client 経由）。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult dataclass を公開（ETL の取得件数、保存件数、品質問題、エラーなどを集約）。
    - _get_max_date 等のユーティリティにより差分取得処理の基盤を提供。
    - デフォルトのバックフィル挙動、カレンダー先読み、品質チェック方針を文書化。

- Research / ファクター算出 (kabusys.research)
  - calc_momentum / calc_volatility / calc_value を提供（prices_daily / raw_financials 参照）。
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - Volatility: 20 日 ATR、ATR 比率、平均売買代金、出来高比率を計算。データ不足時は None を返す。
    - Value: raw_financials の最新財務データと当日の株価から PER / ROE を計算。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターン計算を実装（LEAD を利用）。
    - calc_ic: スピアマンランク相関（情報係数）を実装。3 レコード未満で None を返す安全仕様。
    - rank: 同順位は平均ランクで扱うランク付けユーティリティ（丸めによる ties 対応）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出（None を除外）。
  - 研究向けに pandas 等の外部依存を避け、DuckDB と標準ライブラリのみで実装。

- テスト容易性・ロバストネス設計
  - OpenAI 呼び出し部分は内部関数を patch で差し替え可能にしてユニットテストを容易化。
  - API 呼び出し失敗時は例外を投げずフォールバック（ゼロスコアやスキップ）することでデータ生成パイプラインの耐障害性を確保。
  - DuckDB の仕様差（executemany の空リスト扱い等）を考慮した実装。

### Security
- 環境変数の取り扱いで OS 環境変数を保護する仕組み（protected set）を導入。.env からの上書きで敏感情報が誤って上書きされないよう設計。

### Notes / ドキュメンテーション
- 各モジュールに実装方針・設計上の注意（ルックアヘッドバイアス防止、フェイルセーフ動作、DuckDB の制約等）を明記。
- OpenAI の利用には OPENAI_API_KEY の設定が必須。api_key を引数で注入可能にして CI/テストでの取り回しを容易にしている。

## Deprecated
- （該当なし）

## Removed
- （該当なし）

## Fixed
- （初回リリースのため該当なし）

---

今後のリリースでは、バグ修正・性能改善・追加機能（例: Strategy / Execution の具体的実装、Webhook/通知、より詳細な品質チェックなど）を段階的に反映していきます。変更履歴はセマンティックバージョンに従って更新してください。