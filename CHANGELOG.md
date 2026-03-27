KEEP A CHANGELOG — kabusys

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
リリース方針: 重大変更は Breaking Changes として明記し、それ以外は Added/Changed/Fixed に分類します。

[Unreleased]

0.1.0 - 2026-03-27
------------------
Added
- パッケージ基礎
  - 初期リリース。パッケージ名 kabusys、バージョン 0.1.0 を導入。src/kabusys/__init__.py で公開サブパッケージ（data, research, ai, ...）を定義。

- 環境設定 / 設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を起点に探索するため、CWD に依存しない。
  - .env パーサーの改善:
    - export KEY=val 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - コメント扱いはクォートの有無と直前の空白に基づいて正確に処理。
  - 自動ロードの制御: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - OS 環境変数を保護する protected キーセットを導入し、.env の上書き制御を行う。
  - 必須環境変数取得時のヘルパー _require を提供し、不在時は明確な ValueError を送出。
  - Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / ログレベル / env 判定 等）。KABUSYS_ENV と LOG_LEVEL の検証ロジックを実装（許容値を列挙して検証）。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（news_nlp.py）
    - raw_news と news_symbols を元に、銘柄単位でニュースを集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを算出。
    - 一度に処理する銘柄数の上限（_BATCH_SIZE=20）、1銘柄あたりの最大記事数・文字数トリム制御、JSON mode を利用。
    - 429/ネットワーク断/タイムアウト/5xx を対象に指数バックオフでリトライ。その他エラーはスキップして処理継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーション実装（JSON パース回復ロジック含む）。不整合なレスポンスはスキップ。
    - ai_scores テーブルへの冪等的な置換ロジック（対象コードのみ DELETE → INSERT）により部分失敗時に他のスコアを保護。
    - 単体テスト容易化のため、OpenAI 呼び出し箇所は patch 可能な内部関数として抽象化。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。

  - 市場レジーム判定（regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロニュースはニュース NLP のウィンドウ計算を利用して raw_news からフィルタ取得し、OpenAI で JSON レスポンスを期待して評価。
    - OpenAI 呼び出しはリトライ・エラーハンドリングを実装し、API 失敗時は macro_sentiment=0.0（中立）で継続するフォールバックを採用。
    - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と、書き込み失敗時の ROLLBACK 保護を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（src/kabusys/data）
  - ETL パイプライン（pipeline.py / etl.py）
    - 差分取得、保存（jquants_client を経由した冪等保存）、品質チェックを組み合わせた ETLResult データクラスを導入。
    - 最終取得日の補正（バックフィル）ロジック、カレンダー先読み等の運用上の配慮を反映。
    - DuckDB のテーブル存在チェックや最大日付取得のユーティリティを提供。
    - ETLResult は品質問題・エラー情報を収集し呼び出し元で扱えるように設計。
  - カレンダー管理（calendar_management.py）
    - market_calendar テーブルを用いた営業日判定・次営業日/前営業日の探索・期間内営業日取得ロジックを実装。
    - DB 未取得時は曜日ベースのフォールバック（週末除外）で一貫した判定を行う。
    - calendar_update_job による J-Quants からの差分取得・バックフィル処理を実装し、健全性チェック（未来日付の異常検出）も含む。
    - get_trading_days / next_trading_day / prev_trading_day の最大探索範囲を設定し無限ループを防止。

- Research（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - Momentum（1M/3M/6M リターン、200日 MA 乖離）、Volatility（20日 ATR、相対 ATR）、Liquidity（20日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB 上で計算する関数を実装。
    - データ不足時の None 処理や、営業日ベースでのホライズン計算等を考慮。
    - 出力は (date, code) ベースの辞書リスト。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、Spearman ランク相関（IC）計算、ランク関数、ファクター統計サマリーを実装。
    - 外部ライブラリに依存せず、標準ライブラリのみで完結する設計。欠損値や非有限値の除外ロジックを含む。
  - research パッケージのトップレベルで主要関数を再エクスポート。

- 内部設計上の配慮・フェイルセーフ
  - いずれの分析関数も datetime.today()/date.today() を内部で参照しない（ルックアヘッドバイアス防止）。すべてターゲット日（引数）を基準に動作。
  - OpenAI 呼び出し周りは 429/ネットワーク断/タイムアウト/5xx を中心にリトライを実装し、非致命的なエラーはデフォルトでスキップして進行することで、批処理のロバスト性を確保。
  - DuckDB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、部分失敗時の既存データ保護を意識した削除/挿入戦略を採用。
  - テスト容易性確保のため、OpenAI 呼び出し点を patch 可能な内部関数として抽象化。

Security / Requirements
- 環境変数が設定されていない場合は明確に ValueError を投げる設計（例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- 自動的に .env をロードする際、OS 環境変数を優先し、.env による意図しない上書きを防ぐ仕組みを持つ。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Breaking Changes
- 初回リリースのため該当なし。

Notes / Migration & Usage Tips
- テストや CI で .env の自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI の API キーは関数引数で注入可能（テスト用）で、指定しない場合は環境変数 OPENAI_API_KEY を参照します。
- DuckDB を用いた処理の互換性: executemany に空リストを投げられない制約（DuckDB 0.10 相当）に配慮した実装になっています。古い/将来の DuckDB バージョンでの差異に注意してください。
- ai/news_nlp, ai/regime_detector の OpenAI 呼び出しは JSON モードのレスポンスを期待します。プロンプト設計は厳密な JSON 出力を要求するため、外部 API レスポンスの変化によりパース失敗が発生する可能性があります（その場合は該当チャンクをスキップし、処理を継続します）。

今後の予定（一例）
- PBR・配当利回り等のバリューファクター追加
- ETL の品質チェック強化と自動修復オプション
- OpenAI 呼び出しのユニットテストカバレッジ拡充
- jquants_client の抽象化とモック容易性向上

（終）