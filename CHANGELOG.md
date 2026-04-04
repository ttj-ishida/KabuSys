Keep a Changelog
すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Security: セキュリティ関連

当該CHANGELOGは、与えられたコードベースの内容から実装意図を推測して記載しています。

Unreleased
---------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。公開モジュール: data, strategy, execution, monitoring をエクスポート。
  - パッケージバージョンを __version__ = "0.1.0" として設定。

- 環境設定 / 設定管理 (kabusys.config)
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト用途を意識）。
  - .env パーサを実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを正しく処理
    - インラインコメントの取り扱い（クォートあり/なしでの違い）に対応
  - _load_env_file で OS 環境変数を保護する protected 機構を導入（.env.local による上書きと .env の既存値保護をサポート）。
  - Settings クラスを実装し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / システム環境等のプロパティを提供。必要な環境変数が未設定の場合は明示的に ValueError を送出するように設計。
  - 有効値チェック: KABUSYS_ENV（development, paper_trading, live）と LOG_LEVEL のバリデーションを実装。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント解析（news_nlp）を実装:
    - 指定のニュース時間ウィンドウで raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してスコアを取得。
    - 1銘柄あたり記事数・文字数上限（記事数: 10、文字数: 3000）でトリムし、最大バッチサイズ 20 銘柄で処理。
    - JSON Mode 応答のバリデーションと復元（余分な前後テキストが混ざるケースへの対応）。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx などを指数バックオフでリトライ。致命的でないAPI失敗はスキップして処理を継続するフェイルセーフ設計。
    - DuckDB 互換性考慮: executemany に空リストを渡さない保護（DuckDB 0.10 対応）。
    - ai_scores テーブルへは「対象コードのみ」を DELETE → INSERT により置換して部分失敗時のデータ保護を実現。
    - テスト容易性: OpenAI 呼び出し部分を _call_openai_api 経由にし、単体テスト時に差し替え可能。
  - 市場レジーム判定（regime_detector）を実装:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定。
    - MA 計算時は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。データ不足時は中立値（ma200_ratio=1.0）を採用し WARNING ログを出力。
    - マクロ記事はキーワードベースで抽出し、OpenAI（gpt-4o-mini）で JSON 形式にマクロセンチメントを取得。API エラー時は macro_sentiment=0.0 にフォールバック。
    - スコアはクリップ（-1.0〜1.0）され、閾値により regime_label を決定。
    - market_regime テーブルへは冪等性を考慮した BEGIN / DELETE / INSERT / COMMIT を実施し、失敗時は ROLLBACK を試行。

- データプラットフォーム (kabusys.data)
  - ETL パイプライン基盤（pipeline）を実装:
    - ETLResult データクラスを提供し、取得件数・保存件数・品質問題・エラーを集約。監査ログや検査用に to_dict を提供。
    - 差分更新、バックフィル、品質チェックの設計方針をコードコメントで明示。
  - カレンダー管理（calendar_management）を実装:
    - market_calendar テーブルの利用に基づいた is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - DB にカレンダー情報がない場合は曜日ベースのフォールバック（週末を休場扱い）。
    - next/prev_trading_day は最大探索日数制限を設け、安全性を担保。
    - calendar_update_job を実装し、J-Quants クライアントを使って差分取得・バックフィル（直近数日）の再取得・IDEMPOTENTな保存を実行。健全性チェック（極端に未来の last_date をスキップ）を実装。

- Research ツール群 (kabusys.research)
  - ファクター計算（factor_research）を実装:
    - Momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）。
    - Volatility / Liquidity: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率。
    - Value: PER（EPS が 0/欠損時は None）と ROE（raw_financials からの取得）。
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し、結果を (date, code) ベースの dict リストで返却。
  - 特徴量探索（feature_exploration）を実装:
    - 将来リターン計算（calc_forward_returns）: 指定ホライズンに対する将来終値からのリターンを計算。horizons のバリデーションあり。
    - IC（Information Coefficient）計算（calc_ic）: factor と forward を code で結合し、スピアマンのランク相関（ρ）を計算。十分な有効レコードがない場合は None を返す。
    - ランク関数（rank）: 同順位は平均ランクを採用。丸め処理で ties 判定の安定化。
    - 統計サマリー（factor_summary）: count/mean/std/min/max/median を算出。

Changed
- DuckDB に関する互換性考慮を明文化:
  - executemany に空リストを渡さないガードや、配列バインドの不安定性への回避策を実装。
- AI モジュールのエラー処理設計:
  - LLM 呼び出しの失敗がパイプライン全体を停止させないよう、明確にフェイルセーフを採用。

Fixed
- （この初期リリースでは既知のバグ修正履歴はなし。コード内にログ出力や回復処理を多めに実装し、運用時の堅牢性を高めている旨を反映）

Security
- .env ロード時に OS 環境変数を上書きしない既定の挙動と、上書き時に既存 OS 環境変数を保護する protected パラメータを導入。
- 必須の秘密情報（OpenAI / J-Quants / kabu API のアクセストークン等）は Settings 経由で取得し、未設定時は明示的に ValueError を送出して安全性を担保。

Notes / Implementation details
- OpenAI クライアント呼び出しは gpt-4o-mini を想定し、JSON Mode を利用する想定の実装（response_format={"type": "json_object"}）。
- ニュース窓口の時間は JST ベースで定義され、内部は UTC naive datetime を用いた DB クエリに変換している（ルックアヘッドバイアス対策）。
- DB 書き込みは部分失敗に備えた設計（対象コード絞り込みの DELETE→INSERT、トランザクションの BEGIN/COMMIT/ROLLBACK）を採用。
- テストしやすさを意識して、OpenAI 呼び出しを差し替え可能にする hook（_call_openai_api）を各モジュールに配置。

将来の改善候補（実装上コメントとして触れられている事項）
- PBR・配当利回り等のバリュー指標の追加。
- news_nlp の応答検証を更に強化するためのスキーマ検証。
- ETL の品質チェック結果に対する自動アクション（アラート送信等）の実装。
- execution/monitoring モジュールの具体的な実装（現状 package エクスポートに名前あり、実態は未提供）。

----
（注）上記は提供されたソースコードの実装内容とコメントから推測して作成した変更履歴です。実際のコミット履歴やリリースノートが存在する場合はそれに合わせて調整してください。