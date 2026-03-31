# Changelog

すべての重要な変更をここに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

- リリースはセマンティックバージョニングに従います。  
- 日付は YYYY-MM-DD 形式です。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回リリース — 日本株自動売買 / データ基盤・リサーチ・AI モジュールの基礎を実装。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - 公開サブパッケージ: data, research, ai, monitoring?, strategy?, execution?（__all__ に data, strategy, execution, monitoring を公開）

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの設定自動ロードを実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない自動読み込み。
  - .env パーサ実装:
    - コメント行、`export KEY=val` 形式、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
    - override / protected の概念を持ち、OS 環境変数を保護して .env.local による上書きを制御。
  - Settings クラスを提供（settings インスタンス経由で使用）。
    - 必須設定取得時は _require により未設定で ValueError を発生させる。
    - 各種設定プロパティ:
      - J-Quants / kabuステーション / Slack / データベースパス（DuckDB / SQLite） / 環境種別（development/paper_trading/live） / ログレベル 等。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を用い、銘柄ごとのニュースを収集して OpenAI (gpt-4o-mini) に送ることで銘柄単位のセンチメント ai_score を生成。
  - 時間ウィンドウ（JST 前日 15:00 ～ 当日 08:30）に基づく記事選定（UTC への変換実装）。
  - バッチ処理（最大 20 銘柄 / コール）とトークン肥大化対策（記事数・文字数のトリム）。
  - API 呼び出しは JSON mode を利用し、レスポンスをバリデーション。スコアは ±1 にクリップ。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ実装。
  - DuckDB へは冪等的に（DELETE → INSERT）スコアを書き込む。部分失敗時に既存スコアを保護する実装。
  - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（関数に分離）。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）判定。
  - news_nlp の calc_news_window を利用してマクロ記事を抽出。
  - OpenAI 呼び出し（gpt-4o-mini, JSON mode）・リトライ・フェイルセーフ（API失敗時は macro_sentiment=0.0）。
  - DuckDB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と、例外発生時の ROLLBACK 保護。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計。

- データプラットフォーム（kabusys.data）
  - ETL 用インターフェースの公開（ETLResult 型を pipeline モジュールから再エクスポート）。
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティを追加。
    - 営業日判定 API: is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - カレンダー未取得時は曜日ベースでフォールバックする堅牢なロジック。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存を実装。健全性チェック（過度な未来日付の検出）を追加。
  - pipeline（ETL）
    - 差分取得・保存・品質チェック（quality モジュール想定）を行う ETL 構造と ETLResult データクラスを実装。
    - ETLResult による結果集約（取得数 / 保存数 / 品質問題 / エラーリスト 等）および to_dict() 出力を提供。
    - DuckDB テーブル存在チェック・最大日付取得等のユーティリティを実装。
    - デフォルトのバックフィルやカレンダー先読みのパラメータを設定。

- リサーチ（kabusys.research）
  - ファクター計算と特徴量探索ユーティリティを実装・公開。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の計算。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務データを取得して PER, ROE を計算（PBR 等は未実装）。
    - SQL とウィンドウ関数を活用し DuckDB 上で計算（外部 API にはアクセスしない設計）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを計算（デフォルト [1,5,21]）。
    - calc_ic: スピアマンのランク相関（IC）計算（欠測・同順位・最小サンプル数の考慮）。
    - rank: 同順位は平均ランクとして扱うランク化ユーティリティ（丸めにより tie 検出誤差を低減）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
  - 研究用ユーティリティは外部ライブラリに依存せず標準ライブラリのみで実装。

- その他
  - モジュールのログ出力（logger）を多用して処理状況・警告を詳細に記録するように実装。
  - OpenAI SDK 呼び出し箇所（_call_openai_api）を各モジュールで独立実装し、モジュール間の内部関数共有を避けテスト容易性を向上。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 環境変数による機密情報管理を前提：
  - OpenAI API キーは必須（score_news / score_regime で api_key 引数または環境変数 OPENAI_API_KEY を要求）。
  - Slack トークン、チャンネル ID、Kabu API パスワード、J-Quants トークン等は Settings で必須化。未設定時は ValueError を送出。
- .env 自動ロードはプロジェクトルート検出に基づく。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

### 注意点・設計上の留意事項
- ルックアヘッドバイアス防止:
  - AI モジュールおよびリサーチモジュールは datetime.today()/date.today() を内部で参照せず、呼び出し元から target_date を与える設計。
- フェイルセーフ:
  - LLM 呼び出しの失敗時に例外をそのまま上位に投げず、フェイルセーフ値（例: macro_sentiment = 0.0）で継続する箇所がある。重大な DB 書き込みエラーは例外伝播。
- DuckDB 互換性:
  - executemany に空リストを渡すと失敗する（DuckDB 0.10）点に配慮したガードを実装。
- テスト容易性:
  - OpenAI 呼び出し箇所はモック差し替えが想定されており、ユニットテストでの置換が容易。

## 既知の制限 / 将来の改善候補
- research.calc_value は現時点で PBR や配当利回りを未実装。将来追加予定。
- AI モデル・プロンプトやバッチサイズ、リトライポリシーは運用に応じてチューニング可能。
- calendar_update_job の J-Quants 連携は jq.fetch_market_calendar / jq.save_market_calendar に依存。API 対応・エラーハンドリングの追加改善余地あり。
- monitoring / strategy / execution パッケージの実装詳細は今後拡張予定（現バージョンでは主要モジュールの土台を提供）。

---

訳注: 実装内容はソースコードから推測して記載しています。実際の API クライアント実装（jquants_client 等）や運用ルールに応じて追加の設定・権限・例外処理が必要になる可能性があります。