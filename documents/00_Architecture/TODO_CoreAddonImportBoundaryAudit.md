# Core Import Boundary Audit

`Issue 3` として、`Core` から `Addon` 候補への結合を監査した記録。

この監査では次の 2 種類を分けて見ている。

- `import` 結合
- `Addon` が作るテーブルやページを `Core` が前提にするデータ結合

## 1. 結論

現状の `KabuSys` は、`AI / Yahoo News / Disclosure` については `Core` からの直接 `import` は比較的少ない。  
一方で、`AI` と `Strategy Lab` は `Core` 側にデータ結合が残っている。

優先度順の論点は次のとおり。

1. `signal_generator.py` が `ai_scores` / `market_regime` を直接前提にしている
2. `backtest` が `ai_scores` / `market_regime` を入力前提にしている
3. `dashboard_data.py` に `Strategy Lab` 用ローダーが同居している
4. `scripts/` に Addon 実行入口が本体同居している

## 2. 対象別の監査結果

### 2.1 AI

#### 直接 import

`Core` 本体から `kabusys.ai` への直接 `import` は広くは発生していない。確認できた主な参照は次。

- [scripts/run_ai_analysis.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_ai_analysis.py:19)
- [src/kabusys/ai/regime_detector.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/ai/regime_detector.py:41)
- [src/kabusys/ai/__init__.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/ai/__init__.py:1)

このうち `scripts/run_ai_analysis.py` は Addon 側の入口として扱える。  
`src/kabusys/ai/regime_detector.py` 内の `news_nlp` 参照は Addon 内部結合なので、`Core` / `Addon` 分離の主論点ではない。

#### データ結合

`Core` は AI モジュールを直接 import しなくても、AI が作るテーブルを使っている。

- [src/kabusys/strategy/signal_generator.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/strategy/signal_generator.py:872)
  - `ai_scores` を直接参照
- [src/kabusys/strategy/signal_generator.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/strategy/signal_generator.py:216)
  - `market_regime` を直接参照
- [src/kabusys/backtest/engine.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/backtest/engine.py:92)
  - インメモリ DB に `ai_scores` / `market_regime` をコピー
- [src/kabusys/backtest/run.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/backtest/run.py:10)
  - 事前投入テーブルとして `ai_scores` / `market_regime` を明記
- [src/kabusys/portfolio/risk_adjustment.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/portfolio/risk_adjustment.py:88)
  - `market_regime.regime_label` 前提のロジック

#### 判定

- `import` 境界: `概ね良好`
- データ境界: `✅ 分離済み（Issue #271）`

#### 分離 TODO

- ~~`StrategyEnhancer` か `RegimeProvider` のような `Core` 側 IF を作る~~ ✅ 完了（Issue #271）
- ~~`signal_generator.py` は `ai_scores` / `market_regime` を直接読む代わりに、`Addon` 未導入時フォールバックを明示する~~ ✅ 完了（Issue #271）
- ~~`backtest` は `AI なしで動く Core モード` を別定義する~~ ✅ 完了（Issue #271）

### 2.2 Yahoo News

#### 直接 import

Yahoo News 収集は専用スクリプトに閉じている。

- [scripts/run_yahoonews_collection.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_yahoonews_collection.py:18)
- [src/kabusys/data/news_collector.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/data/news_collector.py:1)

`run_data_update.py` や日次 ETL 本体は `news_collector` を直接呼んでいない。

- [scripts/run_data_update.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_data_update.py:18)

#### データ結合

Yahoo News 自体の収集は `Core` に未接続だが、AI 側は `raw_news` を前提にする。

- [src/kabusys/ai/news_nlp.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/ai/news_nlp.py:111)
- [src/kabusys/ai/regime_detector.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/ai/regime_detector.py:292)

ただし、これは `AI Addon` 内の連携として閉じており、`Core` が `news_collector` を直接 import しているわけではない。

#### 判定

- `import` 境界: `良好`
- データ境界: `AI Addon 内の依存として許容`

#### 分離 TODO

- `run_yahoonews_collection.py` は将来的に `addons` 側へ移設
- `Core` ドキュメントでは Yahoo News を必須導線に書かない

### 2.3 Disclosure

#### 直接 import

TDnet / EDINET / 開示分類は独立スクリプトからのみ呼ばれている。

- [scripts/run_tdnet_collection.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_tdnet_collection.py:17)
- [scripts/run_edinet_collection.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_edinet_collection.py:17)
- [scripts/run_disclosure_classification.py](/C:/Users/tetsu/Projects/KabuSys/scripts/run_disclosure_classification.py:17)

`Core` の通常実行系からこれらを直接 import している箇所は今回の監査では見当たらなかった。

#### データ結合

`EDINET` 側は `TDnet` の保存関数を再利用している。

- [src/kabusys/data/edinet_collector.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/data/edinet_collector.py:41)

これは `Disclosure Addon` 内部の結合であり、`Core` 側の問題ではない。

#### 判定

- `import` 境界: `良好`
- データ境界: `Addon 内部結合のみ`

#### 分離 TODO

- `DisclosureProvider` 単位で Addon repo にまとめる
- `scripts/run_tdnet_collection.py` などの入口を Core 配布物から外せる形にする

### 2.4 Strategy Lab

#### 直接 import

`Streamlit` 本体はページを直接 import していない。

- [src/kabusys/monitoring/streamlit_dashboard.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/monitoring/streamlit_dashboard.py:1)
- ページ実体: [10_Strategy_Lab.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/monitoring/pages/10_Strategy_Lab.py:1)

この点は `Streamlit` の `pages/` 自動検出に乗っているため、`Home` 側の import 結合は薄い。

#### データ結合

**✅ 対応済み（Issue #272 / PR #275）**

`Strategy Lab` 専用のデータ取得関数が `dashboard_data.py` に同居していた問題を解消した。

- [src/kabusys/monitoring/strategy_lab_data.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/monitoring/strategy_lab_data.py)
  - `load_market_regime` / `load_ai_scores` / `load_signal_summary` を新ファイルに分離
- `dashboard_data.py` は Core 運用ページ（Home / Signal Queue / Performance）用ローダーのみを保持

`10_Strategy_Lab.py` は `strategy_lab_data` から import しており、`dashboard_data` への依存が解消された。

#### 判定

- `import` 境界: `良好`
- モジュール配置境界: `✅ 分離済み`

## 3. 設定フラグの監査

`Core` 側には optional 機能のトグルが残っている。

- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:177) `ENABLE_AI_SENTIMENT`
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:186) `ENABLE_TDNET`
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:196) `ENABLE_EDINET`
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:214) `ENABLE_YAHOONEWS`
- [src/kabusys/config.py](/C:/Users/tetsu/Projects/KabuSys/src/kabusys/config.py:232) `LINE_NOTIFY_ENABLED`

現状では `Core` が `Addon` を「設定で無効化できる同居機能」として扱っている。  
別 repo 化を進めるなら、次のどちらかに寄せる必要がある。

- `Core` に最小限のトグルだけ残し、未導入時は常に no-op
- `Addon` 固有フラグを `core` 設定から外し、Addon 側設定へ移す

## 4. 総合判定

### 4.1 すでに境界が良いもの

- Yahoo News 収集
- TDnet / EDINET / 開示分類
- `Strategy Lab` ページファイル自体

理由は、専用スクリプトや専用ページとして孤立度が高く、`Core` 実行系が直接 import していないため。

### 4.2 境界がまだ弱いもの

- `AI` のスコアとレジームを `Core` 戦略が直接前提にしている点
- `backtest` が `ai_scores` / `market_regime` を前提にしている点

## 5. Issue 3 の次アクション

優先順位は次のとおり。

1. ~~`signal_generator.py` の `ai_scores` / `market_regime` 参照を抽象化する~~ ✅ 完了（Issue #271）
2. ~~`backtest` の `Core-only` 入力要件を定義する~~ ✅ 完了（Issue #271）
3. ~~`dashboard_data.py` から `Strategy Lab` ローダーを分離する~~ ✅ 完了（Issue #272 / PR #275）
4. `scripts/run_ai_analysis.py` / `run_yahoonews_collection.py` / `run_tdnet_collection.py` を Addon 配置前提で再整理する

## 6. 関連

- [TODO_CoreAddonRepoSplit.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonRepoSplit.md)
- [TODO_CoreAddonResponsibilityMatrix.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonResponsibilityMatrix.md)
- [TODO_CoreAddonExtensionPoints.md](/C:/Users/tetsu/Projects/KabuSys/documents/00_Architecture/TODO_CoreAddonExtensionPoints.md)
